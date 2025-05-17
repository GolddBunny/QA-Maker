from flask import Blueprint, jsonify, request
import os
import pandas as pd
import tiktoken
import asyncio
from dotenv import load_dotenv

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

question_bp = Blueprint('questionGeneration', __name__)

load_dotenv()

api_key = os.getenv("GRAPHRAG_API_KEY")
llm_model = "gpt-4o-mini"
embedding_model = "text-embedding-3-small"

@question_bp.route('/generate-related-questions', methods=['POST'])
def generate_related_questions():
    data = request.get_json()
    page_id = data.get("page_id")
    question = data.get("question")

    try:
        input_dir = f"../data/input/{page_id}/output"
        db_dir = f"{input_dir}/lancedb/default-entity-description.lance"

        # Load data
        entity_df = pd.read_parquet(f"{input_dir}/entities.parquet")
        community_df = pd.read_parquet(f"{input_dir}/communities.parquet")
        relationship_df = pd.read_parquet(f"{input_dir}/relationships.parquet")
        report_df = pd.read_parquet(f"{input_dir}/community_reports.parquet")
        text_unit_df = pd.read_parquet(f"{input_dir}/text_units.parquet")

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
        - Explore related **topics, entities, attributes, or policies** that are also covered in the data.
        - Vary the focus of each question (e.g., graduation criteria → credit, time, departments, exceptions, etc.).
        - Preferably, cover **other departments**, **different graduation requirements**, **credit details**, **internship conditions**, etc.
        - Do not refer to data tables or technical terms directly.
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

        # 안전하게 기존 루프 재사용 또는 새 루프 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(question_generator.agenerate(
            question_history=[question],
            context_data=None,
            question_count=5
        ))

        return jsonify({"response": result.response})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
