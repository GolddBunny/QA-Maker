import os
import pandas as pd
import tiktoken

from graphrag.config.enums import ModelType
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager
from graphrag.query.indexer_adapters import (
    read_indexer_communities,
    read_indexer_entities,
    read_indexer_reports,
)
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch

# 입력 디렉토리와 쿼리를 상수로 설정
INPUT_DIR = "/Users/jiyoon/Library/Mobile Documents/com~apple~CloudDocs/황금토끼 GraphRAG/2025 캡스톤 프로젝트/domain_qa_system/data/input2/output"
QUERY = "2025년 동계 프로그래밍 캠프 일정과 위치를 알려주세요."

# GraphRAG API 키와 모델 설정
GRAPHRAG_API_KEY = "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"
GRAPHRAG_LLM_MODEL = "gpt-4o-mini"
GRAPHRAG_EMBEDDING_MODEL = "text-embedding-3-small"

# 커뮤니티 테이블 이름 설정
COMMUNITY_TABLE = "communities"
COMMUNITY_REPORT_TABLE = "community_reports"
ENTITY_TABLE = "entities"

# 라이덴 커뮤니티 계층 구조에서 사용할 커뮤니티 레벨 설정
# 값이 높을수록 더 세분화된 커뮤니티에서 보고서를 로드함 (단, 계산 비용이 증가)
COMMUNITY_LEVEL = 2

# 언어 모델 구성 및 초기화
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

# Parquet 파일에서 데이터 로드
community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")

# 인덱서 데이터 읽기
communities = read_indexer_communities(community_df, report_df)
reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)
entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)

# 시스템 프롬프트 파일 로드
global_search_knowledge_system_prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "global_search_knowledge_system_prompt.txt")
with open(global_search_knowledge_system_prompt_path, "r", encoding="utf-8") as file:
    global_search_knowledge_system_prompt = file.read()

global_search_map_system_prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "global_search_map_system_prompt.txt")
with open(global_search_map_system_prompt_path, "r", encoding="utf-8") as file:
    global_search_map_system_prompt = file.read()

global_search_reduce_system_prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "global_search_reduce_system_prompt.txt")
with open(global_search_reduce_system_prompt_path, "r", encoding="utf-8") as file:
    global_search_reduce_system_prompt = file.read()

# 글로벌 커뮤니티 컨텍스트 빌더 생성
context_builder = GlobalCommunityContext(
    community_reports=reports,
    communities=communities,
    entities=entities,  # 커뮤니티 가중치를 사용하지 않으려면 None으로 설정
    token_encoder=token_encoder,
)

# 컨텍스트 빌더 매개변수 설정
context_builder_params = {
    "use_community_summary": False,  # False: 전체 커뮤니티 보고서 사용, True: 커뮤니티 요약 사용
    "shuffle_data": True,           
    "include_community_rank": True,
    "min_community_rank": 0,
    "community_rank_name": "rank",
    "include_community_weight": True,
    "community_weight_name": "occurrence weight",
    "normalize_community_weight": True,
    "max_tokens": 12_000,  # 모델 토큰 제한에 따라 조정 (8k 제한 모델의 경우 5000이 적절)
    "context_name": "Reports",
}

# Map LLM 매개변수 설정
map_llm_params = {
    "max_tokens": 1000,
    "temperature": 0.0,
    "response_format": {"type": "json_object"},
}

# Reduce LLM 매개변수 설정
reduce_llm_params = {
    "max_tokens": 2000,  # 모델 토큰 제한에 따라 조정 (8k 제한 모델의 경우 1000-1500이 적절)
    "temperature": 0.0,
}

# 글로벌 검색 엔진 생성
search_engine = GlobalSearch(
    model=model,
    context_builder=context_builder,
    token_encoder=token_encoder,
    max_data_tokens=12_000,  # 모델 토큰 제한에 따라 조정 (8k 제한 모델의 경우 5000이 적절)
    map_llm_params=map_llm_params,
    reduce_llm_params=reduce_llm_params,
    allow_general_knowledge=False,  # True로 설정하면 LLM이 일반 지식을 응답에 통합하도록 지시 (환각이 증가할 수 있음)
    json_mode=True,  # LLM 모델이 JSON 모드를 지원하지 않는 경우 False로 설정
    context_builder_params=context_builder_params,
    concurrent_coroutines=32,
    response_type="multiple paragraphs",  # 응답 유형 및 형식을 설명하는 자유 형식 텍스트
    global_search_knowledge_system_prompt=global_search_knowledge_system_prompt,
    global_search_map_system_prompt=global_search_map_system_prompt,
    global_search_reduce_system_prompt=global_search_reduce_system_prompt,
)

# 비동기 함수를 동기적으로 실행하기 위한 코드
import asyncio

# 검색 실행
async def run_search():
    result = await search_engine.search(QUERY)
    print(result.response)
    
    # 저장할 디렉토리 경로 설정
    output_dir = os.path.join(os.path.dirname(__file__), "xglobal_context_data")
    os.makedirs(output_dir, exist_ok=True)
    
    for key, df in result.context_data.items():
        if isinstance(df, pd.DataFrame):
            output_file = os.path.join(output_dir, f"context_data_{key}.csv")
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"{key} 데이터가 {output_file}에 저장되었습니다.")
    
    return result

# 비동기 코드 실행
result = asyncio.run(run_search())