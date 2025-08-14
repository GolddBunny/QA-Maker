import os
import subprocess
import pandas as pd
import tiktoken
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pathlib import Path
import io
from flask import Blueprint, jsonify, request, json
from services.graph_service.create_graph import generate_and_save_graph
from graphrag.config.enums import ModelType
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_communities,
    read_indexer_covariates,
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.question_gen.local_gen import LocalQuestionGen
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch
from firebase_config import bucket
from flask_cors import cross_origin
import traceback
query_bp = Blueprint('query', __name__)
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/input"))

# Thread pool for running async code with Flask
thread_pool = ThreadPoolExecutor(max_workers=5)

env_path = Path("../data/parquet/.env")
load_dotenv(dotenv_path=env_path)

GRAPHRAG_API_KEY = os.getenv("GRAPHRAG_API_KEY")
GRAPHRAG_LLM_MODEL = "gpt-4o-mini"
GRAPHRAG_EMBEDDING_MODEL = "text-embedding-3-small"

def run_async(coro):
    """Run a coroutine in a new event loop in a separate thread"""
    loop = asyncio.new_event_loop()
    
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@query_bp.route('/run-local-query', methods=['POST'])
def run_local_query():
    # 외부에서 질문을 받음
    page_id = request.json.get('page_id', '')
    if not page_id:
        return jsonify({'error': 'page_id가 제공되지 않았습니다.'}), 400    
    query_text = request.json.get('query', '')
    if not query_text:
        return jsonify({'error': '질문이 제공되지 않았습니다.'}), 400

    # Define input and database paths
    #INPUT_DIR = f"../data/input/{page_id}/output"
    INPUT_DIR = f"../data/input/{page_id}/output"
    LANCEDB_URI = f"{INPUT_DIR}/lancedb"
    COMMUNITY_REPORT_TABLE = "community_reports"
    ENTITY_TABLE = "entities"
    COMMUNITY_TABLE = "communities"
    RELATIONSHIP_TABLE = "relationships"
    COVARIATE_TABLE = "covariates"
    TEXT_UNIT_TABLE = "text_units"
    COMMUNITY_LEVEL = 2

    # Read nodes table to get community and degree data
    entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
    community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
    entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)

    # Load description embeddings to an in-memory lancedb vectorstore
    # To connect to a remote db, specify url and port values
    description_embedding_store = LanceDBVectorStore(
        collection_name="default-entity-description",
    )
    description_embedding_store.connect(db_uri=LANCEDB_URI)

    # Load relationship data
    relationship_df = pd.read_parquet(f"{INPUT_DIR}/{RELATIONSHIP_TABLE}.parquet")
    relationships = read_indexer_relationships(relationship_df)

    # Load report data
    report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")
    reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)

    # Load text unit data
    text_unit_df = pd.read_parquet(f"{INPUT_DIR}/{TEXT_UNIT_TABLE}.parquet")
    text_units = read_indexer_text_units(text_unit_df)

    # Configure the language model
    api_key = GRAPHRAG_API_KEY
    llm_model = GRAPHRAG_LLM_MODEL
    embedding_model = GRAPHRAG_EMBEDDING_MODEL

    chat_config = LanguageModelConfig(
        api_key=api_key,
        type=ModelType.OpenAIChat,
        model=llm_model,
        max_retries=20,
    )
    chat_model = ModelManager().get_or_create_chat_model(
        name="local_search",
        model_type=ModelType.OpenAIChat,
        config=chat_config,
    )
    token_encoder = tiktoken.encoding_for_model(llm_model)

    embedding_config = LanguageModelConfig(
        api_key=api_key,
        type=ModelType.OpenAIEmbedding,
        model=embedding_model,
        max_retries=20,
    )
    text_embedder = ModelManager().get_or_create_embedding_model(
        name="local_search_embedding",
        model_type=ModelType.OpenAIEmbedding,
        config=embedding_config,
    )

    # Create context builder
    context_builder = LocalSearchMixedContext(
        community_reports=reports,
        text_units=text_units,
        entities=entities,
        relationships=relationships,
        # If you did not run covariates during indexing, set this to None
        # covariates=covariates,
        entity_text_embeddings=description_embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,
        text_embedder=text_embedder,
        token_encoder=token_encoder,
    )

    # Define parameters for local context and model
    local_context_params = {
        "text_unit_prop": 0.5,
        "community_prop": 0.1,
        "conversation_history_max_turns": 0,
        "conversation_history_user_turns_only": True,
        "top_k_mapped_entities": 15,
        "top_k_relationships": 15,
        "include_entity_rank": True,
        "include_relationship_weight": True,
        "include_community_rank": False,
        "return_candidate_context": False,
        "embedding_vectorstore_key": EntityVectorStoreKey.ID,
        "max_tokens": 12_000,
    }

    model_params = {
        "max_tokens": 2_000,
        "temperature": 0.0,
    }

    # Create search engine
    search_engine = LocalSearch(
        model=chat_model,
        context_builder=context_builder,
        token_encoder=token_encoder,
        model_params=model_params,
        context_builder_params=local_context_params,
        response_type="Multi-Page Report",
    )

    try:
        # Run the async search in a separate thread with a dedicated event loop
        result = thread_pool.submit(run_async, search_engine.search(query_text)).result()

        # 결과 저장
        context_files = {}
        for key, df in result.context_data.items():
            if isinstance(df, pd.DataFrame):
                output_file = f"context_data_{key}.csv"
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"👀{key} 데이터가 {output_file}에 저장되었습니다.")
                context_files[key] = output_file

        print("context_data keys:", list(result.context_data.keys()))
        for key, df in result.context_data.items():
            print(f"{key}: type={type(df)}, empty={df.empty if isinstance(df, pd.DataFrame) else 'N/A'}")

        entities_df = pd.read_csv('context_data_entities.csv')
        relationships_df = pd.read_csv('context_data_relationships.csv')

        # 엔티티 ID 리스트 추출
        entities_list = entities_df['id'].astype(int).tolist()

        # 관계 ID 리스트 추출 
        # 관계 데이터프레임의 구조에 따라 필드명 조정 필요
        relationships_list = relationships_df['id'].astype(int).tolist()

        print("entities_list: ", entities_list, 
              "relationships_list: ", relationships_list)

        # 서브 그래프 생성
        generate_and_save_graph(entities_list, relationships_list, page_id)

        return jsonify({
            'response': result.response,
            'context_files': context_files
        })
    except Exception as e:
        print(f"Error in run_local_query: {str(e)}")
        return jsonify({'error': str(e)}), 500


@query_bp.route('/run-global-query', methods=['POST'])
def run_global_query():
#     page_id = request.json.get('page_id', '')

#     query_text = request.json.get('query', '')
#     if not query_text:
#         return jsonify({'error': '질문이 제공되지 않았습니다.'}), 400

#     api_key = GRAPHRAG_API_KEY
#     llm_model = GRAPHRAG_LLM_MODEL

#     config = LanguageModelConfig(
#         api_key=api_key,
#         type=ModelType.OpenAIChat,
#         model=llm_model,
#         max_retries=20,
#     )

#     model = ModelManager().get_or_create_chat_model(
#         name="global_search",
#         model_type=ModelType.OpenAIChat,
#         config=config,
#     )

#     token_encoder = tiktoken.encoding_for_model(llm_model)

#     # 경로
#     INPUT_DIR = f"../data/input/{page_id}/output"
#     COMMUNITY_TABLE = "communities"
#     COMMUNITY_REPORT_TABLE = "community_reports"
#     ENTITY_TABLE = "entities"
#     COMMUNITY_LEVEL = 2

#     community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
#     entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
#     report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")

#     communities = read_indexer_communities(community_df, report_df)
#     reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)
#     entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)

#     context_builder = GlobalCommunityContext(
#         community_reports=reports,
#         communities=communities,
#         entities=entities,
#         token_encoder=token_encoder,
#     )

#     context_builder_params = {
#         "use_community_summary": False,
#         "shuffle_data": True,
#         "include_community_rank": True,
#         "min_community_rank": 0,
#         "community_rank_name": "rank",
#         "include_community_weight": True,
#         "community_weight_name": "occurrence weight",
#         "normalize_community_weight": True,
#         "max_tokens": 12_000,
#         "context_name": "Reports",
#     }

#     map_llm_params = {
#         "max_tokens": 1000,
#         "temperature": 0.0,
#         "response_format": {"type": "json_object"},
#     }

#     reduce_llm_params = {
#         "max_tokens": 2000,
#         "temperature": 0.0,
#     }

#     search_engine = GlobalSearch(
#         model=model,
#         context_builder=context_builder,
#         token_encoder=token_encoder,
#         max_data_tokens=12_000,
#         map_llm_params=map_llm_params,
#         reduce_llm_params=reduce_llm_params,
#         allow_general_knowledge=False,
#         json_mode=True,
#         context_builder_params=context_builder_params,
#         concurrent_coroutines=32,
#         response_type="Multi-Page Report",
#     )

#     try:
#         # Run the async search in a separate thread with a dedicated event loop
#         result = thread_pool.submit(run_async, search_engine.search(query_text)).result()

#         # 결과 저장
#         context_files = {}
#         for key, df in result.context_data.items():
#             if isinstance(df, pd.DataFrame):
#                 output_file = f"context_data_{key}.csv"
#                 df.to_csv(output_file, index=False, encoding='utf-8-sig')
#                 print(f"{key} 데이터가 {output_file}에 저장되었습니다.")
#                 context_files[key] = output_file

#         return jsonify({
#             'response': result.response
#         })
#     except Exception as e:
#         print(f"Error in run_global_query: {str(e)}")
#         return jsonify({'error': str(e)}), 500
    page_id = request.json.get('page_id', '')
    if not page_id:
        return jsonify({'error': 'page_id가 제공되지 않았습니다.'}), 400

    query_text = request.json.get('query', '')
    if not query_text:
        return jsonify({'error': '질문이 제공되지 않았습니다.'}), 400

    try:
        # graphrag 실행을 별도 쓰레드에서 처리
        result = thread_pool.submit(run_graphrag_query, page_id, query_text).result()

        return jsonify({
            'response': result
        })
    except Exception as e:
        print(f"Error in run_local_query: {str(e)}")
        return jsonify({'error': str(e)}), 500


def run_graphrag_query(page_id, message):
    try:
        INPUT_DIR = f"../data/input/{page_id}"
        command = [
            'graphrag',
            'query',
            '--root', INPUT_DIR,
            '--response-type', "Multi-Page Report",
            '--method', 'basic',
            '--query', message
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0:
            print(f"graphrag 오류 발생: {result.stderr}")
            raise Exception(f"graphrag 실행 오류: {result.stderr.strip()}")

        return result.stdout.strip()
    except Exception as e:
        raise RuntimeError(f"run_graphrag_query 실패: {str(e)}")


@query_bp.route('/generate-graph', methods=['POST'])
def generate_graph():    
    try:
        return jsonify({
            'success': True,
            # 'entities_count': len(entities_list),
            # 'relationships_count': len(relationships_list)
        })
    except FileNotFoundError as e:
        return jsonify({'error': f'필요한 CSV 파일을 찾을 수 없습니다: {str(e)}'}), 404
    except Exception as e:
        print(f"Error in generate_graph: {str(e)}")
        return jsonify({'error': str(e)}), 500

@query_bp.route('/admin/all-graph', methods=['POST'])
def all_graph():
    page_id = request.json.get('page_id', '')

    try:
        # 절대 경로로 안전하게 설정
        base_path = os.path.join(BASE_PATH, str(page_id), "output")
        #print("base_path:", base_path)

        prefix = f'pages/{page_id}/results/'

        blobs = list(bucket.list_blobs(prefix=prefix))

        blob_dict = {}
        for blob in blobs:
            filename = blob.name.replace(prefix, '')
            if filename:
                blob_dict[filename] = blob.download_as_bytes()
        # 파이어베이스의 파케이 읽어서 가져오게 
        # entities_df = pd.read_parquet(io.BytesIO(blob_dict["entities.parquet"]))
        # relationships_df = pd.read_parquet(io.BytesIO(blob_dict["relationships.parquet"]))
        entities_parquet = os.path.join(base_path, "entities.parquet")
        relationships_parquet = os.path.join(base_path, "relationships.parquet")

        entities_df = pd.read_parquet(entities_parquet)
        relationships_df = pd.read_parquet(relationships_parquet)

        # entities: degree 기준 상위 100개
        top_entities = (
            entities_df
            .sort_values(by='degree', ascending=False)
            .head(120)
            ['human_readable_id']
            .astype(int)
            .tolist()
        )

        # relationships: weight 기준 상위 100개
        top_relationships = (
            relationships_df
            .sort_values(by='weight', ascending=False)
            .head(100)
            ['human_readable_id']
            .astype(int)
            .tolist()
        )
        # GraphML / JSON 절대 경로
        graphml_path = os.path.abspath(os.path.join(BASE_PATH, "../../data/graphs", str(page_id), "all_graph.graphml"))
        json_path = os.path.abspath(os.path.join(BASE_PATH, "../../frontend/public/json", str(page_id), "admin_graphml_data.json"))

        # print(f"graphml_path exists: {os.path.exists(os.path.dirname(graphml_path))}")
        # print(f"json_path exists: {os.path.exists(os.path.dirname(json_path))}")

        os.makedirs(os.path.dirname(graphml_path), exist_ok=True)
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        # 그래프 생성 및 저장
        # generate_and_save_graph(
        #     entities_df['human_readable_id'].astype(int).tolist(),
        #     relationships_df['human_readable_id'].astype(int).tolist(),
        #     page_id,
        #     graphml_path=graphml_path,
        #     json_path=json_path
        # )
        generate_and_save_graph(
            top_entities,
            top_relationships,
            page_id,
            graphml_path=graphml_path,
            json_path=json_path
        )

        # 저장된 JSON 파일을 읽어서 응답
        with open(json_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)

        return jsonify(graph_data)

    except Exception as e:
        print(f"[Graph 생성 에러]: {e}")
        return jsonify({"success": False, "error": str(e)}), 500