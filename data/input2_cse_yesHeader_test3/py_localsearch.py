import os
import pandas as pd
import tiktoken
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.vector_stores.lancedb import LanceDBVectorStore

from graphrag.config.enums import ModelType
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager
from pathlib import Path

# 입력 및 데이터베이스 경로 정의
INPUT_DIR = Path(__file__).parent / "output"
# query = "프로그래밍 캠프의 날짜를 알려주세요."
query = "모바일소프트웨어트랙 소속 교수님들을 모두 빠짐없이 알려주세요."
# query = "황기태 교수님에 대해 알려주세요."
# query = "웹공학트랙 소속 교수님들을 모두 빠짐없이 알려주세요."
# query = "모바일소프트웨어트랙의 필수 교과목을 모두 알려주세요."
# query = "모바일소프트웨어트랙의 4학년 1학기 과목을 모두 빠짐없이 알려주세요."
# query = "정보보안 과목을 4학년 2학기에 들을 수 있나요?"
# query = "운영체제 과목에 대해서 상담받고 싶은데, 어느 교수님께 가서 상담을 받아야 하나요?"
# query = "운영체제를 전공하는 학생에게 조언을 잘 해줄 수 있는 교수님은 누구인가요?"
# query = "금융권에 취업하고 싶은데 관련 활동을 할 수 있는 프로그램이 있나요?"

LANCEDB_URI = f"{INPUT_DIR}/lancedb"
COMMUNITY_REPORT_TABLE = "community_reports"
ENTITY_TABLE = "entities"
COMMUNITY_TABLE = "communities"
RELATIONSHIP_TABLE = "relationships"
TEXT_UNIT_TABLE = "text_units"
COMMUNITY_LEVEL = 2

# 커뮤니티 및 연결 정도 데이터를 얻기 위해 노드 테이블 읽기
entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)

# 설명 임베딩을 인메모리 lancedb 벡터 저장소에 로드
# 원격 DB에 연결하려면 url 및 port 값을 지정
description_embedding_store = LanceDBVectorStore(
    collection_name="default-entity-description",
)
description_embedding_store.connect(db_uri=LANCEDB_URI)

# 관계 데이터 로드
relationship_df = pd.read_parquet(f"{INPUT_DIR}/{RELATIONSHIP_TABLE}.parquet")
relationships = read_indexer_relationships(relationship_df)

# 보고서 데이터 로드
report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")
reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)

# 텍스트 단위 데이터 로드
text_unit_df = pd.read_parquet(f"{INPUT_DIR}/{TEXT_UNIT_TABLE}.parquet")
text_units = read_indexer_text_units(text_unit_df)

# 시스템 프롬프트 파일 로드
prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "local_search_system_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as file:
    system_prompt = file.read()


# API 키 및 모델 정의
GRAPHRAG_API_KEY = "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"
GRAPHRAG_LLM_MODEL = "gpt-4o"
# GRAPHRAG_LLM_MODEL = "gpt-4.1-mini"
GRAPHRAG_EMBEDDING_MODEL = "text-embedding-3-small"
# GRAPHRAG_EMBEDDING_MODEL = "text-embedding-ada-002"

# 언어 모델 구성
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

# 컨텍스트 빌더 생성
context_builder = LocalSearchMixedContext(
    community_reports=reports,
    text_units=text_units,
    entities=entities,
    relationships=relationships,
    entity_text_embeddings=description_embedding_store,
    embedding_vectorstore_key=EntityVectorStoreKey.ID,  # 벡터 저장소가 ID로 엔티티 제목을 사용하는 경우 EntityVectorStoreKey.TITLE로 설정
    text_embedder=text_embedder,
    token_encoder=token_encoder,
)

# 로컬 컨텍스트 및 모델을 위한 매개변수 정의
local_context_params = {
    "text_unit_prop": 0.4,
    "community_prop": 0.1,
    "conversation_history_max_turns": 0,          # 대화 기록의 최대 턴 수
    "conversation_history_user_turns_only": True, # 사용자 턴만 대화 기록에 포함
    "top_k_mapped_entities": 30,
    "top_k_relationships": 30,
    "include_entity_rank": True,
    "include_relationship_weight": True,
    "include_community_rank": False,        
    "return_candidate_context": False,       # 후보 컨텍스트 반환 여부
    "embedding_vectorstore_key": EntityVectorStoreKey.ID,  # 벡터 저장소가 엔티티 제목을 ID로 사용하는 경우 EntityVectorStoreKey.TITLE로 설정
    "max_tokens": 18_000,  # 모델에서 가지고 있는 토큰 제한에 따라 변경하세요
}

model_params = {
    # "max_tokens": 2_000,  # 모델에서 가지고 있는 토큰 제한에 따라 변경하세요
    # "temperature": 0.0,   # 0.0은 예측 확률이 높은 결과를 선택하는 것을 의미
}

# 검색 엔진 생성
search_engine = LocalSearch(
    model=chat_model,
    context_builder=context_builder,
    token_encoder=token_encoder,
    # model_params=model_params,
    context_builder_params=local_context_params,
    # response_type="multiple paragraphs",  # 응답 유형 및 형식을 설명하는 자유 형식 텍스트
    # response_type="Single Page",
    # response_type="List of 3-7 Points",
    response_type="Multi-Page Report",
    system_prompt=system_prompt
)

# 검색을 실행하는 비동기 함수 정의
async def run_search(query):
    result = await search_engine.search(query)
    print(result.response)

    # 저장할 디렉토리 경로 설정
    output_dir = os.path.join(os.path.dirname(__file__), "xlocal_context_data")
    os.makedirs(output_dir, exist_ok=True)
    
    for key, df in result.context_data.items():
        if isinstance(df, pd.DataFrame):
            output_file = os.path.join(output_dir, f"{key}.csv")
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"{key} 데이터가 {output_file}에 저장되었습니다.")

# 파일을 직접 실행하는 경우 검색 실행
if __name__ == "__main__":
    import asyncio
    asyncio.run(run_search(query))