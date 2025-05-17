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

load_dotenv()

api_key = os.getenv("GRAPHRAG_API_KEY")
llm_model = "gpt-3.5-turbo"
embedding_model = "text-embedding-3-small"

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

INPUT_DIR = "../data/input/1747110168282/output"
ENTITY_TABLE = "entities"
COMMUNITY_TABLE = "communities"

entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
community_level = 0
entities = read_indexer_entities(entity_df, community_df, community_level )
relationship_df = pd.read_parquet(f"{INPUT_DIR}/relationships.parquet")
relationships = read_indexer_relationships(relationship_df)
report_df = pd.read_parquet(f"{INPUT_DIR}/community_reports.parquet")
reports = read_indexer_reports(report_df, community_df, community_level)
text_unit_df = pd.read_parquet(f"{INPUT_DIR}/text_units.parquet")
text_units = read_indexer_text_units(text_unit_df)

class CustomLanceDBVectorStore(LanceDBVectorStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        db_uri = kwargs.get("db_dir").replace('/default-entity-description.lance', '')
        self.connect(db_uri=db_uri)

description_embedding_store = CustomLanceDBVectorStore(
    collection_name="default-entity-description",
    db_dir="../data/input/1747110168282/output/lancedb/default-entity-description.lance",
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

async def generate_questions():
    question_history = [
        "한성대학교 이사장이 누구야?"
    ]
    candidate_questions = await question_generator.agenerate(
        question_history=question_history, context_data=None, question_count=5
    )
    print(candidate_questions.response)

if __name__ == "__main__":
    asyncio.run(generate_questions())
