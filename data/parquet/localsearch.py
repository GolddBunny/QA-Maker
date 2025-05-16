# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License.
import os
import pandas as pd
import tiktoken
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

from graphrag.config.enums import ModelType
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager

# Define input and database paths
INPUT_DIR = "/Users/jy/Documents/Domain_QA_Gen/data/input/1746882791795/output"
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
#print(f"Entity count: {len(entity_df)}")
#print(entity_df.head())

# Load relationship data
relationship_df = pd.read_parquet(f"{INPUT_DIR}/{RELATIONSHIP_TABLE}.parquet")
relationships = read_indexer_relationships(relationship_df)
#print(f"Relationship count: {len(relationship_df)}")
#print(relationship_df.head())

# Load report data
report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")
reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)
#print(f"Report records: {len(report_df)}")
#print(report_df.head())

# Load text unit data
text_unit_df = pd.read_parquet(f"{INPUT_DIR}/{TEXT_UNIT_TABLE}.parquet")
text_units = read_indexer_text_units(text_unit_df)
#print(f"Text unit records: {len(text_unit_df)}")
#print(text_unit_df.head())

# Define API keys and models
GRAPHRAG_API_KEY = "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"
GRAPHRAG_LLM_MODEL = "gpt-4o-mini"
GRAPHRAG_EMBEDDING_MODEL = "text-embedding-3-small"

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
    embedding_vectorstore_key=EntityVectorStoreKey.ID,  # If the vectorstore uses entity title as ids, set this to EntityVectorStoreKey.TITLE
    text_embedder=text_embedder,
    token_encoder=token_encoder,
)

# Define parameters for local context and model
local_context_params = {
    "text_unit_prop": 0.5,
    "community_prop": 0.1,
    "conversation_history_max_turns": 5,
    "conversation_history_user_turns_only": True,
    "top_k_mapped_entities": 20,
    "top_k_relationships": 20,
    "include_entity_rank": True,
    "include_relationship_weight": True,
    "include_community_rank": False,
    "return_candidate_context": False,
    "embedding_vectorstore_key": EntityVectorStoreKey.ID,  # Set this to EntityVectorStoreKey.TITLE if the vectorstore uses entity title as ids
    "max_tokens": 12_000,  # Change this based on the token limit you have on your model
}

model_params = {
    "max_tokens": 2_000,  # Change this based on the token limit you have on your model
    "temperature": 0.0,
}

# Create search engine
search_engine = LocalSearch(
    model=chat_model,
    context_builder=context_builder,
    token_encoder=token_encoder,
    model_params=model_params,
    context_builder_params=local_context_params,
    response_type="multiple paragraphs",  # Free form text describing the response type and format
)

# Define an async function to run the search
async def run_search():
    result = await search_engine.search("graphrag 관련 내용은 어느 파일에 나와있어?")
    print(result.response)
    
    # print(result.context_data["entities"])
    # print(result.context_data["relationships"])
    
    # if "reports" in result.context_data:
    #     print(result.context_data["reports"].head())
    
    # print(result.context_data["sources"].head())
    
    # if "claims" in result.context_data:
    #     print(result.context_data["claims"].head())
    
    for key, df in result.context_data.items():
        if isinstance(df, pd.DataFrame):
            output_file = f"context_data_{key}.csv"
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"{key} 데이터가 {output_file}에 저장되었습니다.")

# If running the file directly, execute the search
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_search())