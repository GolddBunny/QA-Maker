import os
import pandas as pd
import tiktoken
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pathlib import Path

from flask import Blueprint, jsonify, request
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

query_bp = Blueprint('query', __name__)

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
        "top_k_mapped_entities": 10,
        "top_k_relationships": 10,
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
        response_type="multiple paragraphs",
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
                print(f"{key} 데이터가 {output_file}에 저장되었습니다.")
                context_files[key] = output_file
        
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
    page_id = request.json.get('page_id', '')

    query_text = request.json.get('query', '')
    if not query_text:
        return jsonify({'error': '질문이 제공되지 않았습니다.'}), 400

    api_key = GRAPHRAG_API_KEY
    llm_model = GRAPHRAG_LLM_MODEL

    config = LanguageModelConfig(
        api_key=api_key,
        type=ModelType.OpenAIChat,
        model=llm_model,
        max_retries=20,
    )

    model = ModelManager().get_or_create_chat_model(
        name="global_search",
        model_type=ModelType.OpenAIChat,
        config=config,
    )

    token_encoder = tiktoken.encoding_for_model(llm_model)

    # 경로
    INPUT_DIR = f"../data/input/{page_id}/output"
    COMMUNITY_TABLE = "communities"
    COMMUNITY_REPORT_TABLE = "community_reports"
    ENTITY_TABLE = "entities"
    COMMUNITY_LEVEL = 2

    community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
    entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
    report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")

    communities = read_indexer_communities(community_df, report_df)
    reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)
    entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)

    context_builder = GlobalCommunityContext(
        community_reports=reports,
        communities=communities,
        entities=entities,
        token_encoder=token_encoder,
    )

    context_builder_params = {
        "use_community_summary": False,
        "shuffle_data": True,
        "include_community_rank": True,
        "min_community_rank": 0,
        "community_rank_name": "rank",
        "include_community_weight": True,
        "community_weight_name": "occurrence weight",
        "normalize_community_weight": True,
        "max_tokens": 12_000,
        "context_name": "Reports",
    }

    map_llm_params = {
        "max_tokens": 1000,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    reduce_llm_params = {
        "max_tokens": 2000,
        "temperature": 0.0,
    }

    search_engine = GlobalSearch(
        model=model,
        context_builder=context_builder,
        token_encoder=token_encoder,
        max_data_tokens=12_000,
        map_llm_params=map_llm_params,
        reduce_llm_params=reduce_llm_params,
        allow_general_knowledge=False,
        json_mode=True,
        context_builder_params=context_builder_params,
        concurrent_coroutines=32,
        response_type="multiple paragraphs",
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
                print(f"{key} 데이터가 {output_file}에 저장되었습니다.")
                context_files[key] = output_file
        
        return jsonify({
            'response': result.response,
            'context_files': context_files
        })
    except Exception as e:
        print(f"Error in run_global_query: {str(e)}")
        return jsonify({'error': str(e)}), 500

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