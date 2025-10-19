import asyncio
from openai import AsyncOpenAI
from concurrent.futures import ThreadPoolExecutor
import time
import os
import re
from typing import List, Tuple, Dict, Any
from dotenv import load_dotenv
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()
api_key = os.getenv("GRAPHRAG_API_KEY", "").strip()
# AsyncOpenAI 클라이언트 초기화
async_client = AsyncOpenAI(api_key=api_key)

class OptimizedLLMEvaluator:
    """비동기 및 배치 처리로 최적화된 LLM 평가 클래스"""
    
    def __init__(self, model: str = "gpt-4o-mini", max_concurrent: int = 5):
        self.model = model
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def _safe_llm_call(self, prompt: str, temperature: float = 0) -> str:
        """비동기 LLM 호출 with rate limiting"""
        async with self.semaphore:
            try:
                response = await async_client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"LLM 호출 오류: {e}")
                return ""
    
    async def extract_statements_and_check_support_batch(
        self, answer: str, contexts: List[str]
    ) -> Tuple[List[str], List[float]]:
        """진술 추출과 지원도 체크를 한 번에 처리 (통합 프롬프트)"""
        
        contexts_text = "\n".join(contexts)
        
        # 통합 프롬프트: 진술 추출 + 각 진술의 지원도 평가를 한 번에
        prompt = f"""
다음 답변에서 사실적 진술을 추출하고, 각 진술이 Context에서 얼마나 뒷받침되는지 평가해주세요.

답변: {answer}

Context:
{contexts_text}

작업:
1. 답변에서 개별적인 사실적 진술들을 추출 (조언/권유 제외)
2. 각 진술이 Context에서 얼마나 뒷받침되는지 0.0~1.0 점수로 평가

평가 기준:
- 완전히 동일하거나 명시적으로 뒷받침: 1.0
- 추론 가능하고 뒷받침 분명: 0.9
- 관련 있음: 0.8
- 약간 관련: 0.6
- 전혀 없음/모순: 0.0

출력 형식 (반드시 준수):
1. [진술 내용] | [점수]
2. [진술 내용] | [점수]
...

진술이 없으면 "진술 없음"
"""
        
        content = await self._safe_llm_call(prompt)
        
        # 파싱
        statements = []
        scores = []
        for line in content.split('\n'):
            line = line.strip()
            if '|' in line and re.match(r'\d+\.', line):
                parts = line.split('|')
                if len(parts) == 2:
                    statement = re.sub(r'^\d+\.\s*', '', parts[0]).strip()
                    try:
                        score = float(parts[1].strip())
                        statements.append(statement)
                        scores.append(score)
                    except:
                        pass
        
        return statements, scores
    
    async def generate_reverse_question(self, answer: str) -> str:
        """비동기 역질문 생성"""
        prompt = f"""
다음 답변을 바탕으로 원래 질문이 무엇이었을지 추측하여 질문을 생성해주세요.

답변: {answer}

생성된 질문만 답해주세요.
"""
        return await self._safe_llm_call(prompt)
    
    async def extract_key_information(self, question: str) -> List[str]:
        """비동기 핵심 정보 추출"""
        prompt = f"""
다음 질문에서 답변에 필요한 핵심 정보 개념을 추출해주세요.

질문: {question}

규칙:
- 날짜, 숫자 등 구체적 값 제외
- 질문에 등장한 개념어 중심
- 간결하고 일반화된 형태

출력 형식:
1. [핵심 정보 1]
2. [핵심 정보 2]
...

핵심 정보가 없으면 "정보 없음"
"""
        content = await self._safe_llm_call(prompt)
        
        key_info = []
        for line in content.split('\n'):
            line = line.strip()
            if re.match(r'\d+\.', line):
                info = re.sub(r'^\d+\.\s*', '', line).strip()
                if info and info != "정보 없음":
                    key_info.append(info)
        
        return key_info if key_info else ["기본 정보"]
    
    async def check_answer_accuracy_batch(
        self, key_infos: List[str], context: str, answer: str
    ) -> List[float]:
        """여러 핵심 정보의 답변 정확도를 배치로 평가"""
        
        infos_text = "\n".join([f"{i+1}. {info}" for i, info in enumerate(key_infos)])
        
        prompt = f"""
다음 각 핵심 정보(info)에 대해 context 포함 여부와 answer 반영 여부를 평가해주세요.

핵심 정보 목록:
{infos_text}

Context: {context}
Answer: {answer}

평가 기준:
- Context 포함: 정확(+0.5), 유사(+0.4), 없음(0.0)
- Answer 반영: 정확(+0.5), 추론가능(+0.4), 유사(+0.3), 없음(0.0)

출력 형식 (각 줄마다):
1. [context점수], [answer점수]
2. [context점수], [answer점수]
...

예: 1. 0.5, 0.4
"""
        
        content = await self._safe_llm_call(prompt)
        
        scores = []
        lines = content.strip().split('\n')
        for i, line in enumerate(lines):
            if i >= len(key_infos):
                break
            numbers = re.findall(r'\d+\.?\d*', line)
            if len(numbers) >= 2:
                total = min(float(numbers[0]) + float(numbers[1]), 1.0)
                scores.append(round(total, 3))
        
        # 부족한 경우 0.0으로 채우기
        while len(scores) < len(key_infos):
            scores.append(0.0)
        
        return scores


class OptimizedAccuracyCalculator:
    """비동기 처리로 최적화된 정확도 계산 클래스"""
    
    def __init__(self):
        self.weights = [0.40, 0.35, 0.25]
        self.metric_names = ['faithfulness', 'answer_relevancy', 'context_recall']
        self.llm_evaluator = OptimizedLLMEvaluator(max_concurrent=5)
        self.embedding_model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
    
    async def calculate_faithfulness_async(
        self, answer: str, contexts: List[str]
    ) -> float:
        """비동기 신실성 계산"""
        if not answer.strip():
            return 0.0
        
        statements, scores = await self.llm_evaluator.extract_statements_and_check_support_batch(
            answer, contexts
        )
        
        if not statements:
            return 1.0
        
        faithfulness = sum(scores) / len(statements)
        return round(faithfulness, 3)
    
    async def calculate_relevancy_async(
        self, question: str, answer: str
    ) -> float:
        """비동기 관련성 계산"""
        if not question.strip() or not answer.strip():
            return 0.0
        
        reverse_question = await self.llm_evaluator.generate_reverse_question(answer)
        
        # 임베딩 계산은 동기적으로 (빠름)
        similarity = self._calculate_cosine_similarity(question, reverse_question)
        return round(min(1.0, similarity), 3)
    
    async def calculate_recall_async(
        self, contexts: List[str], answer: str, question: str
    ) -> float:
        """비동기 재현율 계산"""
        if not contexts:
            return 1.0
        
        # 핵심 정보 추출
        required_info = await self.llm_evaluator.extract_key_information(question)
        
        if not required_info:
            return 1.0
        
        # 배치로 답변 정확도 평가
        contexts_combined = ' '.join(contexts)
        scores = await self.llm_evaluator.check_answer_accuracy_batch(
            required_info, contexts_combined, answer
        )
        
        recall = sum(scores) / len(scores) if scores else 1.0
        return round(recall, 3)
    
    def _calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        """SBERT 기반 코사인 유사도 (동기)"""
        try:
            emb1 = self.embedding_model.encode(text1, convert_to_tensor=True)
            emb2 = self.embedding_model.encode(text2, convert_to_tensor=True)
            
            emb1_np = emb1.cpu().detach().numpy().reshape(1, -1)
            emb2_np = emb2.cpu().detach().numpy().reshape(1, -1)
            
            similarity = cosine_similarity(emb1_np, emb2_np)[0][0]
            return float(similarity)
        except Exception as e:
            print(f"유사도 계산 실패: {e}")
            return 0.0
    
    async def calculate_accuracy_async(
        self, question: str, answer: str, contexts: List[str]
    ) -> Dict[str, Any]:
        """비동기 병렬 정확도 계산 - 메인 함수"""
        
        start_time = time.time()
        
        # 세 가지 메트릭을 병렬로 계산
        results = await asyncio.gather(
            self.calculate_faithfulness_async(answer, contexts),
            self.calculate_relevancy_async(question, answer),
            self.calculate_recall_async(contexts, answer, question),
            return_exceptions=True
        )
        
        # 에러 처리
        metrics = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"메트릭 {self.metric_names[i]} 계산 오류: {result}")
                metrics.append(0.0)
            else:
                metrics.append(result)
        
        # 가중치 적용
        total_score = sum(w * m for w, m in zip(self.weights, metrics))
        
        elapsed = time.time() - start_time
        print(f"⏱️ 총 계산 시간: {elapsed:.2f}초")
        
        grade_info = self._get_grade(total_score)
        
        return {
            'total_accuracy': round(total_score, 3),
            'percentage': round(total_score * 100, 1),
            'grade': grade_info['grade'],
            'level': grade_info['level'],
            'metrics': {
                name: score for name, score in zip(self.metric_names, metrics)
            },
            'weights': {
                name: weight for name, weight in zip(self.metric_names, self.weights)
            },
            'calculation_time': round(elapsed, 2)
        }
    
    def _get_grade(self, total_score: float) -> Dict[str, str]:
        """등급 판정"""
        if total_score >= 0.95:
            return {"grade": "A+", "level": "최우수"}
        elif total_score >= 0.85:
            return {"grade": "A", "level": "우수"}
        elif total_score >= 0.75:
            return {"grade": "B", "level": "양호"}
        elif total_score >= 0.65:
            return {"grade": "C", "level": "기본"}
        else:
            return {"grade": "D", "level": "미흡"}


# 사용 예시
def calculate_accuracy_optimized(question: str, answer: str, contexts: List[str]):
    """Flask나 ThreadPool 환경에서도 안전하게 비동기 함수 실행"""
    calculator = OptimizedAccuracyCalculator()
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    result = new_loop.run_until_complete(
        calculator.calculate_accuracy_async(question, answer, contexts)
    )
    new_loop.close()
    return result


def read_csv_as_text_list(file_path: str) -> list[str]:
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        # 모든 셀을 문자열로 변환해서 한 줄씩 합침
        lines = df.astype(str).apply(lambda row: ' | '.join(row), axis=1).tolist()
        return lines
    except Exception as e:
        print(f"CSV 읽기 오류 ({file_path}): {e}")
        return []

# thread_pool = ThreadPoolExecutor(max_workers=5)

# GRAPHRAG_API_KEY = os.getenv("GRAPHRAG_API_KEY")
# GRAPHRAG_LLM_MODEL = "gpt-4o-mini"
# GRAPHRAG_EMBEDDING_MODEL = "text-embedding-3-small"

# def run_async(coro):
#     """Run a coroutine in a new event loop in a separate thread"""
#     loop = asyncio.new_event_loop()
    
#     try:
#         return loop.run_until_complete(coro)
#     finally:
#         loop.close()
        
# def run_local_query(query_text):
#     # INPUT_DIR 하드코딩 제거
#     INPUT_DIR = "/Users/jy/Documents/Domain_QA_Gen/data/input/1747480728566_학교/output"
#     LANCEDB_URI = f"{INPUT_DIR}/lancedb"
    
#     # Load data
#     entity_df = pd.read_parquet(f"{INPUT_DIR}/entities.parquet")
#     community_df = pd.read_parquet(f"{INPUT_DIR}/communities.parquet")
#     entities = read_indexer_entities(entity_df, community_df, 2)

#     description_embedding_store = LanceDBVectorStore(collection_name="default-entity-description")
#     description_embedding_store.connect(db_uri=LANCEDB_URI)

#     relationship_df = pd.read_parquet(f"{INPUT_DIR}/relationships.parquet")
#     relationships = read_indexer_relationships(relationship_df)

#     report_df = pd.read_parquet(f"{INPUT_DIR}/community_reports.parquet")
#     reports = read_indexer_reports(report_df, community_df, 2)

#     text_unit_df = pd.read_parquet(f"{INPUT_DIR}/text_units.parquet")
#     text_units = read_indexer_text_units(text_unit_df)

#     # 모델 설정
#     chat_config = LanguageModelConfig(
#         api_key=GRAPHRAG_API_KEY,
#         type=ModelType.OpenAIChat,
#         model=GRAPHRAG_LLM_MODEL,
#         max_retries=20,
#     )
#     chat_model = ModelManager().get_or_create_chat_model(
#         name="local_search",
#         model_type=ModelType.OpenAIChat,
#         config=chat_config,
#     )
#     token_encoder = tiktoken.encoding_for_model(GRAPHRAG_LLM_MODEL)

#     embedding_config = LanguageModelConfig(
#         api_key=GRAPHRAG_API_KEY,
#         type=ModelType.OpenAIEmbedding,
#         model=GRAPHRAG_EMBEDDING_MODEL,
#         max_retries=20,
#     )
#     text_embedder = ModelManager().get_or_create_embedding_model("local_search_embedding", ModelType.OpenAIEmbedding, config=embedding_config,)

#     context_builder = LocalSearchMixedContext(
#         community_reports=reports,
#         text_units=text_units,
#         entities=entities,
#         relationships=relationships,
#         entity_text_embeddings=description_embedding_store,
#         embedding_vectorstore_key=EntityVectorStoreKey.ID,
#         text_embedder=text_embedder,
#         token_encoder=token_encoder,
#     )

#     search_engine = LocalSearch(
#         model=chat_model,
#         context_builder=context_builder,
#         token_encoder=token_encoder,
#         model_params={"max_tokens": 2000, "temperature": 0.0},
#         context_builder_params={
#             "text_unit_prop": 0.5,
#             "community_prop": 0.1,
#             "conversation_history_max_turns": 0,
#             "conversation_history_user_turns_only": True,
#             "top_k_mapped_entities": 10,
#             "top_k_relationships": 10,
#             "include_entity_rank": True,
#             "include_relationship_weight": True,
#             "include_community_rank": False,
#             "return_candidate_context": False,
#             "embedding_vectorstore_key": EntityVectorStoreKey.ID,
#             "max_tokens": 12000,
#         },
#         response_type="multiple paragraphs",
#     )

#     #result = thread_pool.submit(run_async, search_engine.search(query_text)).result()
#     result = run_async(search_engine.search(query_text))

#     # context 저장
#     context_files = {}
#     for key, df in result.context_data.items():
#         if isinstance(df, pd.DataFrame):
#             output_file = f"context_data_{key}.csv"
#             df.to_csv(output_file, index=False, encoding='utf-8-sig')
#             context_files[key] = output_file

#     return {
#         'response': result.response
#     }

# def main():
#     """사용자 인터페이스"""
#     print("QAGen 범용 정확도 계산기")
#     print("=" * 50)
    
#     load_dotenv()
#     api_key = os.getenv("GRAPHRAG_API_KEY", "").strip()
    
#     # 계산기 초기화
#     if api_key:
#         llm_evaluator = LLMEvaluator(api_key=api_key)
#     else:
#         print("API 키 없이 폴백 모드로 실행합니다.")
#         llm_evaluator = LLMEvaluator()
    
#     calculator = AccuracyCalculator(llm_evaluator)
    
#     while True:
#         print("\n" + "="*50)
#         print("새로운 QA 평가 (종료: 'quit')")
#         print("="*50)
        
#         # 사용자 입력
#         question = input("질문: ").strip()
#         if question.lower() == 'quit':
#             break
        
#         result = run_local_query(question)

#         answer = result.get('response')
#         print("서버 답변:", answer)
        
#         context_files = [
#             "./context_data_entities.csv",
#             "./context_data_relationships.csv",
#             "./context_data_reports.csv",
#             "./context_data_sources.csv"
#         ]
#         contexts = []
#         for file in context_files:
#             contexts.extend(read_csv_as_text_list(file))

#         try:
#             print("\n계산 중...")
#             result = calculator.calculate_accuracy(question, answer, contexts)
            
#             # 결과 출력
#             print("\n" + "평가 결과")
#             print("="*30)
#             print(f"최종 정확도: {result['percentage']}%")
#             print(f"등급: {result['grade']} ({result['level']})")
            
#             print("\n세부 점수:")
#             for name, score in result['metrics'].items():
#                 weight = result['weights'][name]
#                 print(f"  • {name}: {score} (가중치: {weight})")
            
#             print("\n계산 과정:")
#             for breakdown in result['detailed_breakdown'].values():
#                 print(f"  • {breakdown}")
            
#             total_sum = sum(result['weights'][name] * result['metrics'][name] 
#                            for name in result['metric_names'])
#             print(f"  = {round(total_sum, 3)}")
            
#         except Exception as e:
#             print(f"오류 발생: {e}")

# if __name__ == "__main__":
#     main() 