from io import BytesIO
from flask import Blueprint, jsonify, request
import os
import pandas as pd
import tiktoken
import asyncio
import threading
import uuid
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from graphrag.config.enums import ModelType
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.question_gen.local_gen import LocalQuestionGen
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.vector_stores.lancedb import LanceDBVectorStore

from firebase_config import bucket

# Flask에서 async 작업을 돌리기 위해 ThreadPool 사용
thread_pool = ThreadPoolExecutor(max_workers=10)
question_bp = Blueprint('questionGeneration', __name__)

load_dotenv()

api_key = os.getenv("GRAPHRAG_API_KEY")
llm_model = "gpt-4o-mini"
embedding_model = "text-embedding-3-small"

# 스레드 로컬 저장소 (각 스레드마다 독립적인 모델 매니저)
thread_local = threading.local()

def read_parquet_from_firebase(bucket_path: str) -> pd.DataFrame:
    """
    Firebase Storage에 있는 parquet 파일을 바로 읽어서
    DataFrame으로 반환하는 함수
    """
    blob = bucket.blob(bucket_path)

    if not blob.exists():
        raise FileNotFoundError(f"Firebase path does not exist: {bucket_path}")

    data = blob.download_as_bytes()  # 바이트 스트림으로 다운로드
    return pd.read_parquet(BytesIO(data))  # 메모리 버퍼로 읽기

def run_async_question_gen(coro):
    """
    각 스레드에서 독립적인 이벤트 루프 생성 및 실행
    기존 루프와의 충돌 방지
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            print(f"루프 정리 중 오류: {e}")
        finally:
            loop.close()
            asyncio.set_event_loop(None)

def create_fresh_models():
    """
    매 요청마다 완전히 새로운 모델 생성
    기존 캐시를 사용하지 않음
    """
    import uuid
    unique_id = str(uuid.uuid4())[:8]  # 고유 ID 생성
    
    # 완전히 새로운 ModelManager 인스턴스
    model_manager = ModelManager()
    
    # 챗 모델 구성
    chat_config = LanguageModelConfig(
        api_key=api_key,
        type=ModelType.OpenAIChat,
        model=llm_model,
        max_retries=20,
    )
    
    # 고유한 이름으로 새 모델 생성 (캐싱 방지)
    chat_model = model_manager.get_or_create_chat_model(
        name=f"question_gen_chat_{unique_id}",
        model_type=ModelType.OpenAIChat,
        config=chat_config,
    )

    # 임베딩 모델 구성
    embedding_config = LanguageModelConfig(
        api_key=api_key,
        type=ModelType.OpenAIEmbedding,
        model=embedding_model,
        max_retries=20,
    )
    
    text_embedder = model_manager.get_or_create_embedding_model(
        name=f"question_gen_embedding_{unique_id}",
        model_type=ModelType.OpenAIEmbedding,
        config=embedding_config,
    )
    
    return chat_model, text_embedder
    
@question_bp.route('/generate-related-questions', methods=['POST', 'OPTIONS'])
def generate_related_questions():
    # CORS preflight 요청 처리
    if request.method == 'OPTIONS':
        return jsonify({"message": "CORS preflight"}), 200
        
    data = request.get_json()
    page_id = data.get("page_id")
    question = data.get("question")

    if not page_id or not question:
        return jsonify({"error": "page_id와 question이 필요합니다"}), 400

    def generate_questions():
        """별도 스레드에서 질문 생성 실행"""
        # 로컬 경로 설정
        input_dir = f"../data/input/{page_id}/output"
        db_dir = f"{input_dir}/lancedb/default-entity-description.lance"

        # 로컬 파일 사용
        entity_df = pd.read_parquet(f"{input_dir}/entities.parquet")
        community_df = pd.read_parquet(f"{input_dir}/communities.parquet")
        relationship_df = pd.read_parquet(f"{input_dir}/relationships.parquet")
        report_df = pd.read_parquet(f"{input_dir}/community_reports.parquet")
        text_unit_df = pd.read_parquet(f"{input_dir}/text_units.parquet")

        # 데이터 전처리
        entities = read_indexer_entities(entity_df, community_df, 0)
        relationships = read_indexer_relationships(relationship_df)
        reports = read_indexer_reports(report_df, community_df, 0)
        text_units = read_indexer_text_units(text_unit_df)

        # LanceDB 벡터 스토어 커스텀 클래스
        class CustomLanceDBVectorStore(LanceDBVectorStore):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                # 경로에서 파일 이름 제거 후 connect
                db_uri = kwargs.get("db_dir").replace('/default-entity-description.lance', '')
                self.connect(db_uri=db_uri)

        # 설명 벡터를 로드
        description_embedding_store = CustomLanceDBVectorStore(
            collection_name="default-entity-description",
            db_dir=db_dir,
        )

        # 토큰 인코더 생성
        token_encoder = tiktoken.encoding_for_model(llm_model)

        # 매 요청마다 완전히 새로운 모델 생성
        chat_model, text_embedder = create_fresh_models()

        # 로컬 검색 컨텍스트 빌더 생성
        context_builder = LocalSearchMixedContext(
            community_reports=reports,
            text_units=text_units,
            entities=entities,
            relationships=relationships,
            covariates=None,
            entity_text_embeddings=description_embedding_store,
            embedding_vectorstore_key=EntityVectorStoreKey.ID,
            text_embedder=text_embedder,
            token_encoder=token_encoder,
        )

        # 로컬 검색 관련 파라미터
        local_context_params = {
            "text_unit_prop": 0.5,
            "community_prop": 0.1,
            "conversation_history_max_turns": 5,
            "conversation_history_user_turns_only": True,
            "top_k_mapped_entities": 10,
            "top_k_relationships": 10,
            "include_entity_rank": True,
            "include_relationship_weight": True,
            "include_community_rank": False,
            "return_candidate_context": False,
            "embedding_vectorstore_key": EntityVectorStoreKey.ID,
            "max_tokens": 12000,
            "temperature": 0.3,
        }

        custom_system_prompt = """
        ---Role---

        You are a helpful assistant generating a **diverse** bulleted list of {question_count} follow-up questions based on a user's question and the available data. 
        Your responses must be in Korean.

        ---Data tables---

        {context_data}

        ---Goal---

        Given the example question(s) provided by the user, generate a bulleted list of diverse, relevant candidate questions. Use - marks as bullet points.

        Guidelines:
        - Do NOT repeat the same question using different wording.
        - Explore related **topics, entities, attribute** that are also covered in the data.
        - Vary the focus of each question (e.g., graduation criteria → credit, time, departments, exceptions, etc.).
        - Preferably, cover **other departments**, **different graduation requirements**, **credit details**, **internship conditions**, etc.
        - Do not refer to data tables or technical terms directly.
        - The candidate questions should be answerable using the data tables provided, but should not mention any specific data fields or data tables in the question text.
        - Stay within the scope of the data content.

        Your responses must be in Korean.

        ---Example questions---
        """

        # 질문 생성기 초기화
        question_generator = LocalQuestionGen(
            model=chat_model,
            context_builder=context_builder,
            token_encoder=token_encoder,
            context_builder_params=local_context_params,
            system_prompt=custom_system_prompt,
        )

        # 독립적인 이벤트 루프에서 질문 생성 실행
        result = run_async_question_gen(question_generator.generate(
            question_history=[question],
            context_data=None,
            question_count=3
        ))

        return result.response

    try:
        # 별도 스레드에서 질문 생성 실행
        response = thread_pool.submit(generate_questions).result(timeout=60)
        print("Generated questions:", response)
        return jsonify({"response": response})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500