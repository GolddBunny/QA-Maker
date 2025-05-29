from io import BytesIO
from flask import Blueprint, jsonify, request
import os
import pandas as pd
import tiktoken
import asyncio
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

from routes.query_routes import run_async
from firebase_config import bucket

thread_pool = ThreadPoolExecutor(max_workers=5)
question_bp = Blueprint('questionGeneration', __name__)

load_dotenv()

api_key = os.getenv("GRAPHRAG_API_KEY")
llm_model = "gpt-4o-mini"
embedding_model = "text-embedding-3-small"

def read_parquet_from_firebase(bucket_path: str) -> pd.DataFrame:
    """
    Firebase Storage에서 parquet 파일을 직접 읽어 BytesIO로 처리 후 DataFrame으로 반환
    """
    blob = bucket.blob(bucket_path)

    if not blob.exists():
        raise FileNotFoundError(f"Firebase path does not exist: {bucket_path}")

    data = blob.download_as_bytes()  # Blob을 byte stream으로 읽음
    return pd.read_parquet(BytesIO(data))  # 메모리 버퍼로 읽기
    
@question_bp.route('/generate-related-questions', methods=['POST', 'OPTIONS'])
def generate_related_questions():
    data = request.get_json()
    page_id = data.get("page_id")
    question = data.get("question")

    try:
        input_dir = f"../data/input/{page_id}/output"
        db_dir = f"{input_dir}/lancedb/default-entity-description.lance"

        firebase_prefix = f"pages/{page_id}/results"

        entity_df = read_parquet_from_firebase(f"{firebase_prefix}/entities.parquet")
        community_df = read_parquet_from_firebase(f"{firebase_prefix}/communities.parquet")
        relationship_df = read_parquet_from_firebase(f"{firebase_prefix}/relationships.parquet")
        report_df = read_parquet_from_firebase(f"{firebase_prefix}/community_reports.parquet")
        text_unit_df = read_parquet_from_firebase(f"{firebase_prefix}/text_units.parquet")

        # Preprocess
        entities = read_indexer_entities(entity_df, community_df, 0)
        relationships = read_indexer_relationships(relationship_df)
        reports = read_indexer_reports(report_df, community_df, 0)
        text_units = read_indexer_text_units(text_unit_df)

        class CustomLanceDBVectorStore(LanceDBVectorStore):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                db_uri = kwargs.get("db_dir").replace('/default-entity-description.lance', '')
                self.connect(db_uri=db_uri)

        description_embedding_store = CustomLanceDBVectorStore(
            collection_name="default-entity-description",
            db_dir=db_dir,
        )

        # 모델 설정
        token_encoder = tiktoken.encoding_for_model(llm_model)

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
            "temperature": 0.5,
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

        question_generator = LocalQuestionGen(
            model=chat_model,
            context_builder=context_builder,
            token_encoder=token_encoder,
            context_builder_params=local_context_params,
            system_prompt=custom_system_prompt,
        )

        def run_generation():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(question_generator.generate(
                    question_history=[question],
                    context_data=None,
                    question_count=3
                ))
            finally:
                loop.close()
        
        # 별도 스레드에서 실행
        result = thread_pool.submit(run_generation).result()

        print("Generated questions:", result.response)
        return jsonify({"response": result.response})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500