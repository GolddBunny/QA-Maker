import asyncio
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import SentenceTransformer
import tiktoken
import re
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from openai import OpenAI
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
from dotenv import load_dotenv
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

load_dotenv()
api_key = os.getenv("GRAPHRAG_API_KEY", "").strip()
client= OpenAI(api_key=api_key)

@dataclass
class QAEvaluation:
    question: str
    answer: str
    contexts: List[str]
    ground_truth: Optional[str] = None

class LLMEvaluator:
    """LLM을 사용한 텍스트 평가 클래스"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.model = model
    
    def extract_statements(self, text: str) -> List[str]:
        """LLM을 사용하여 텍스트에서 진술 추출"""
        prompt = f"""
                다음 텍스트에서 개별적인 사실적 진술들을 추출해주세요. 각 진술은 하나의 완전한 정보를 담고 있어야 합니다.

                텍스트: {text}

                결과를 다음 형식으로 반환해주세요:
                1. [진술1]
                2. [진술2]
                3. [진술3]
                ...

                진술이 없으면 "진술 없음"이라고 답해주세요.
                """
        
        try:
            response = client.chat.completions.create(model=self.model, 
                                                      messages=[{"role": "user", "content": prompt}], 
                                                      temperature=0)
            
            content = response.choices[0].message.content
            
            # 번호가 있는 리스트에서 진술 추출
            statements = []
            for line in content.split('\n'):
                line = line.strip()
                if re.match(r'\d+\.', line):
                    statement = re.sub(r'^\d+\.\s*', '', line).strip()
                    if statement and statement != "진술 없음":
                        statements.append(statement)
            #print("Extracted statements:", statements)
            return statements
            
        except Exception as e:
            print(f"LLM 진술 추출 오류: {e}")
            # 폴백: 간단한 문장 분리
            return self._fallback_extract_statements(text)
    
    def _fallback_extract_statements(self, text: str) -> List[str]:
        """LLM 실패 시 폴백 진술 추출"""
        sentences = re.split(r'[.!?。]', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def check_statement_support(self, statement: str, contexts: List[str]) -> float:
        """LLM을 사용하여 진술이 컨텍스트에서 얼마나 직접적으로 지원되는지 점수화 (0.0 ~ 1.0)"""
        contexts_text = "\n".join(contexts)

        prompt = f"""
        Statement와 Context가 주어졌습니다. Statement가 Context에 얼마나 잘 뒷받침되는지 다음 기준에 따라 점수를 0.0~1.0 사이로 매겨 주세요.

        Statement: "{statement}"

        Context:
        {contexts_text}

        판정 기준:
        - 완전히 동일한 문장이 있거나, 사실적으로 명시되어 있으면 1.0점
        - 추론을 약간 요구하지만, 뒷받침이 분명하면 0.9점
        - 복잡한 추론이 필요한 경우 0.8점
        - 약간 관련은 있지만 불확실하거나 일부 누락된 경우 0.6점
        - 전혀 언급되지 않았거나 모순되는 경우 0.0점

        형식: 점수만 숫자 형태로 반환 (예: "0.8")
        """

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = response.choices[0].message.content.strip()
            print("지원 점수 응답 내용:", content)

            # 점수 파싱
            score = float(re.findall(r"([0-1](?:\.\d+)?)", content)[0])
            return max(0.0, min(score, 1.0))

        except Exception as e:
            print(f"LLM 지원 점수 확인 오류: {e}")
            # fallback: 키워드 기반 유사도
            return self._fallback_check_support(statement, contexts)
    
    def _fallback_check_support(self, statement: str, contexts: List[str]) -> bool:
        """LLM 실패 시 폴백 지원 확인"""
        from difflib import SequenceMatcher

        joined_context = " ".join(contexts)
        ratio = SequenceMatcher(None, statement, joined_context).ratio()
        return round(min(max(ratio, 0.0), 1.0), 2)
    
    def generate_reverse_question(self, answer: str) -> str:
        """LLM을 사용하여 답변에서 역질문 생성"""
        prompt = f"""
                    다음 답변을 바탕으로 원래 질문이 무엇이었을지 추측하여 질문을 생성해주세요.

                    답변: {answer}

                    생성된 질문만 답해주세요. 설명은 불필요합니다.
                    """
        
        try:
            response = client.chat.completions.create(model=self.model, 
                                                      messages=[{"role": "user", "content": prompt}], 
                                                      temperature=0)
            print("generate reverse question 답변 : ",  response.choices[0].message.content)
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"LLM 역질문 생성 오류: {e}")
            return self._fallback_generate_question(answer)
    
    def _fallback_generate_question(self, answer: str) -> str:
        """LLM 실패 시 폴백 질문 생성"""
        # 간단한 패턴 매칭으로 질문 생성
        if re.search(r'\d+년', answer):
            return "언제인가요?"
        elif re.search(r'\d+학점', answer):
            return "몇 학점인가요?"
        elif "위치" in answer or "주소" in answer:
            return "어디인가요?"
        else:
            return "무엇인가요?"

class AccuracyCalculator:
    """정확도 계산 메인 클래스"""
    
    def __init__(self, llm_evaluator: LLMEvaluator = None):
        self.weights = [0.45, 0.35, 0.20]  # faithfulness, relevancy, recall
        self.metric_names = ['faithfulness', 'answer_relevancy','context_recall']
        self.llm_evaluator = llm_evaluator or LLMEvaluator()
        self.vectorizer = TfidfVectorizer()
        self.model = "gpt-4o-mini"
        self.embedding_model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

    def safe_llm_call(self, prompt: str, temperature: float = 0) -> str:
        """안전한 LLM 호출 메서드 - 누락된 메서드 추가"""
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM 호출 오류: {e}")
            return ""

    def calculate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """신실성 계산: LLM으로 평가, 코드로 계산"""
        print("신실성 계산 시작")
        start_time = time.time()

        if not answer.strip():
            return 0.0
        
        # LLM으로 진술 추출
        statements = self.llm_evaluator.extract_statements(answer)
        
        if not statements:
            elapsed = time.time() - start_time
            print(f"신실성 계산 종료: {elapsed:.2f}초")
            return 1.0  # 진술이 없으면 완벽한 신실성
        
        # LLM으로 각 진술의 지원 여부 확인
        total_score = 0.0
        for statement in statements:
            score = self.llm_evaluator.check_statement_support(statement, contexts)
            print(f"🧾 진술: {statement} → 점수: {score}")
            total_score += score

        faithfulness = total_score / len(statements)
        print(f"✅ 신실성 점수 (정량): {faithfulness:.3f}")
        print(f"⏱️ 완료 시간: {time.time() - start_time:.2f}초")
        return round(faithfulness, 3)
    
    def calculate_relevancy(self, question: str, answer: str) -> float:
        """답변 관련성 계산: 코드로 계산"""

        print("관련성 계산 시작")
        start_time = time.time()

        if not question.strip() or not answer.strip():
            return 0.0
        
        # LLM으로 역질문 생성
        reverse_question = self.llm_evaluator.generate_reverse_question(answer)
        
        # 코사인 유사도 계산은 코드로
        similarity = self._calculate_cosine_similarity(question, reverse_question)
        print("similarity 점수: ", similarity)
        
        similarity = min(1.0, similarity)
        elapsed = time.time() - start_time
        print(f"✅ 관련성 계산 완료: {elapsed:.2f}초")
        return round(similarity, 3)
    
    # def calculate_precision(self, contexts: List[str], question: str) -> float:
    #     """
    #     Context Precision 계산 (LLM 기반, Batch 처리)
    #     → 유용한 context(질문과 관련된)의 비율
    #     """
    #     import time
    #     print("📊 Context Precision 계산 시작")
    #     start_time = time.time()

    #     if not contexts or not question.strip():
    #         return 0.0

    #     is_useful_list = self._check_contexts_usefulness_batch(contexts, question)
    #     relevant_count = sum(is_useful_list)

    #     precision = relevant_count / len(contexts)
    #     elapsed = time.time() - start_time
    #     print(f"✅ Context Precision 계산 완료: {elapsed:.2f}초")
    #     print(f"유용한 문서 수: {relevant_count}/{len(contexts)}")
    #     print("precision 값: ", precision)
    #     return round(min(precision + 0.5, 1.0), 3)
    
    def _check_contexts_usefulness_batch(self, contexts: List[str], question: str) -> List[bool]:
        """
        여러 context를 한 번에 평가하여 유용 여부 리스트로 반환
        """
        prompt = f"""
    다음 질문에 대해 각 컨텍스트가 유용한지 판정해주세요.

    질문: "{question}"

    각 컨텍스트마다 "유용함" 또는 "유용하지 않음"으로만 판정해 주세요.

    형식:
    1. 유용함
    2. 유용하지 않음
    ...

    컨텍스트 목록:
    """

        for i, ctx in enumerate(contexts, start=1):
            prompt += f"{i}. {ctx}\n"

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            content = response.choices[0].message.content.strip()
            print("LLM 응답 결과:\n", content)

            # 결과 파싱
            lines = content.splitlines()
            result_flags = []
            for line in lines:
                if "유용함" in line:
                    result_flags.append(True)
                elif "유용하지 않음" in line:
                    result_flags.append(False)

            # fallback: 리스트 길이 안 맞으면 전부 False
            if len(result_flags) != len(contexts):
                print("⚠️ 판정 수 불일치, 전부 False 처리")
                return [False] * len(contexts)

            return result_flags

        except Exception as e:
            print(f"LLM 배치 판정 오류: {e}")
            return [self._fallback_check_usefulness(ctx, question) for ctx in contexts]
    
    def _fallback_check_usefulness(self, context: str, question: str) -> bool:
        """LLM 실패 시 폴백 유용성 판정"""
        question_words = set(re.findall(r'\w+', question.lower()))
        context_words = set(re.findall(r'\w+', context.lower()))
        
        if not context_words:
            return False
        
        # 질문 단어와 컨텍스트 단어의 겹치는 비율 계산
        overlap = len(question_words.intersection(context_words))
        relevance_ratio = overlap / len(question_words)
        
        # 15% 이상 겹치면 유용한 문서로 간주
        return relevance_ratio >= 0.15
    

    def calculate_recall(self, contexts: List[str], answer: str, question: str) -> float:
        """컨텍스트 재현율 계산: Ground Truth의 정보가 검색된 컨텍스트에 얼마나 포함되어 있는가"""
        print("recall 계산 시작")
        start_time = time.time()

        required_info = self._extract_key_information(question)

        if not required_info or not contexts:
            print("required_info 또는 context 없음")
            return 1.0

        #print(f"검증할 핵심 정보: {required_info}")
        #print(f"검색된 컨텍스트: {contexts}")
        #print(f"AI 답변: {answer}")
        
        total_score = 0
        max_score = len(required_info)
        
        contexts_combined = ' '.join(contexts)
        
        for i, info in enumerate(required_info):
            print(f"\n--- 핵심 정보 {i+1}: '{info}' 검증 ---")
            
            # 단계 2: 핵심 정보가 컨텍스트에 있는지 확인
            context_has_info = self._check_info_in_context(info, contexts_combined)
            #print(f"컨텍스트에 정보 존재: {context_has_info}")
            
            if not context_has_info:
                print(f"❌ 컨텍스트에 '{info}' 정보 없음 - 0점")
                continue
            
            # 단계 3: 컨텍스트의 정보가 답변에 제대로 반영되었는지 확인
            answer_accuracy = self._check_answer_accuracy(info, contexts_combined, answer)
            print(f"답변 정확도: {answer_accuracy}")
            
            if answer_accuracy >= 0.8:  # 80% 이상 정확
                score = 1.0
                print(f"✅ 완전한 정보 반영 - 1점")
            elif answer_accuracy >= 0.5:  # 50% 이상 정확 (부분적)
                score = 0.7
                print(f"⚠️ 부분적 정보 반영 - 0.5점")
            elif answer_accuracy >= 0.2:
                score = 0.4
                print("부정확 (많은 오류 또는 왜곡)")
            else:  # 50% 미만
                score = 0.0
                print(f"❌ 부정확한 정보 반영 - 0점")
            
            total_score += score
        
        # 최종 recall 계산
        recall = total_score / max_score if max_score > 0 else 1.0
        
        print(f"\n📊 최종 결과:")
        print(f"총 점수: {total_score}/{max_score}")
        print(f"Context Recall: {recall}")
        
        elapsed = time.time() - start_time
        print(f"✅ recall 계산 완료: {elapsed:.2f}초")

        return round(recall, 3)
    
    def _check_info_in_context(self, info: str, contexts: str) -> bool:
        """핵심 정보가 컨텍스트에 있는지 확인"""
        
        prompt = f"""
        다음 핵심 정보가 주어진 컨텍스트에 포함되어 있는지 판단해주세요.
        
        핵심 정보: "{info}"
        컨텍스트: "{contexts}"
        
        판단 기준:
        1. 핵심 정보에 대한 직접적인 답변이 컨텍스트에 있는가?
        2. 핵심 정보를 추론할 수 있는 내용이 컨텍스트에 있는가?
        3. 유사한 의미의 표현이 컨텍스트에 있는가?
        
        "예" 또는 "아니오"로만 답해주세요.
        """
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            answer = response.choices[0].message.content.strip().lower()
            return "예" in answer or "yes" in answer
            
        except Exception as e:
            print(f"컨텍스트 확인 실패: {e}")
            # 폴백: 키워드 유사도
            return self._semantic_similarity(info, contexts) > 0.3

    def _check_answer_accuracy(self, info: str, context: str, answer: str) -> float:
        """컨텍스트의 정보가 답변에 정확히 반영되었는지 확인"""
        
        prompt = f"""
        다음 상황을 분석해주세요:
        
        요구된 정보: "{info}"
        컨텍스트의 정보: "{context}"
        AI의 답변: "{answer}"
        
        AI의 답변이 컨텍스트의 정보를 얼마나 정확하게 반영했는지 평가해주세요.
        
        평가 기준:
        1. 컨텍스트의 정보를 정확히 그대로 사용했는가?
        2. 컨텍스트에 없는 내용을 추가했는가? (감점 요소)
        3. 컨텍스트의 정보를 왜곡했는가? (감점 요소)
        4. 컨텍스트의 일부 정보만 사용했는가? (감점 요소)
        
        점수를 0.0에서 1.0 사이로 평가해주세요.
        - 1.0: 완벽하게 정확
        - 0.8: 대부분 정확 (약간의 표현 차이)
        - 0.5: 부분적으로 정확 (일부 정보 누락 또는 추가)
        - 0.2: 부정확 (많은 오류 또는 왜곡)
        - 0.0: 완전히 틀림
        
        점수만 숫자로 답해주세요 (예: 0.8)
        """
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            score_text = response.choices[0].message.content.strip()
            
            # 숫자 추출
            import re
            score_match = re.search(r'(\d+\.?\d*)', score_text)
            if score_match:
                score = float(score_match.group(1))
                return min(1.0, max(0.0, score))  # 0.0~1.0 범위로 제한
            else:
                return 0.5  # 기본값
                
        except Exception as e:
            print(f"답변 정확도 확인 실패: {e}")
            # 폴백: 의미적 유사도
            return self._semantic_similarity(context, answer)

    def _semantic_similarity(self, text1: str, text2: str) -> float:
        """의미적 유사도 계산 (임베딩 기반)"""
        
        try:
            # 1. OpenAI 임베딩 사용 (추천)
            embedding1 = self._get_embedding(text1)
            embedding2 = self._get_embedding(text2)
            
            # 코사인 유사도 계산
            similarity = cosine_similarity([embedding1], [embedding2])[0][0]
            return float(similarity)
            
        except Exception as e:
            print(f"임베딩 기반 유사도 계산 실패: {e}")
            # 폴백: TF-IDF 기반 유사도
            return self._fallback_semantic_similarity(text1, text2)

    def _get_embedding(self, text: str) -> List[float]:
        """텍스트의 임베딩 벡터 획득"""
        
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",  # 또는 "text-embedding-ada-002"
                input=text
            )
            return response.data[0].embedding
            
        except Exception as e:
            print(f"임베딩 생성 실패: {e}")
            # 폴백: 랜덤 벡터 (실제로는 다른 방법 사용)
            raise e

    def _fallback_semantic_similarity(self, text1: str, text2: str) -> float:
        """폴백: TF-IDF 기반 의미적 유사도"""
        
        # TF-IDF 벡터화
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        
        # 코사인 유사도 계산
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)

    def _extract_key_information(self, question: str) -> List[str]:
        """사용자 질문에서 답변에 필요한 핵심 정보 추출"""
        
        prompt = f"""
        다음 질문에서 '완전한 답변을 위해 필요한 핵심 정보 개념'을 추출해주세요.

        - 날짜, 숫자, 시기 등 구체적인 수치나 값은 제외합니다.
        - 질문에 직접적으로 등장한 개념어(명사 중심)를 중심으로, 답변을 위해 필요한 주요 정보 항목을 일반화된 형태로 추출합니다.
        - 정보는 "무엇에 대한 정보인가?"를 기준으로 간결하고 일반화된 형태로 기술해주세요.
        - 단어 중심, 개념 중심의 추출을 목표로 하며, 설명이나 범주는 포함하지 마세요.

        예시:
        질문: "한성대학교 컴퓨터공학과 교수진은 몇 명이고, 주요 연구분야는 무엇인가요?"
        핵심 정보:
        1. 교수진 인원
        2. 연구분야
        3. 컴퓨터공학과

        질문: "파이썬 리스트의 특징과 사용법은 무엇인가요?"
        핵심 정보:
        1. 리스트 특징
        2. 리스트 사용법
        3. 파이썬

        질문: "2023학년 2월 입학생은 몇 년도에 졸업이야?"
        핵심 정보:
        1. 입학생
        2. 졸업
        3. 연도

        결과는 아래 형식으로 반환해주세요:
        1. [핵심 정보 1]
        2. [핵심 정보 2]
        3. [핵심 정보 3]

        핵심 정보가 없다면 "정보 없음"이라고 답해주세요.

        질문: {question}
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            content = response.choices[0].message.content
            print(f"질문에서 추출된 핵심 정보: {content}")
            
            # 번호가 있는 리스트에서 핵심 정보 추출
            key_info = []
            for line in content.split('\n'):
                line = line.strip()
                if re.match(r'\d+\.', line):
                    info = re.sub(r'^\d+\.\s*', '', line).strip()
                    if info and info != "정보 없음":
                        key_info.append(info)
            
            return key_info if key_info else ["기본 정보"]
            
        except Exception as e:
            print(f"핵심 정보 추출 실패: {e}")
            return ["기본 정보"]

    def _fallback_extract_key_info(self, text: str) -> List[str]:
        """폴백: 간단한 문장 분리"""
        sentences = re.split(r'[.!?。]', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        """SBERT 기반 코사인 유사도 계산"""
        try:
            emb1 = self.embedding_model.encode(text1, convert_to_tensor=True)
            emb2 = self.embedding_model.encode(text2, convert_to_tensor=True)

            emb1_np = emb1.cpu().detach().numpy().reshape(1, -1)
            emb2_np = emb2.cpu().detach().numpy().reshape(1, -1)

            similarity = cosine_similarity(emb1_np, emb2_np)[0][0]
            return float(similarity)
        except Exception as e:
            print(f"[오류] SBERT 유사도 계산 실패: {e}")
            return 0.0


    def calculate_accuracy(self, question: str, answer: str, contexts: List[str]) -> Dict[str, Any]:
        """메인 정확도 계산 함수"""
        
        # 1. 각 메트릭 계산 (LLM 평가 + 코드 계산)
        faithfulness = self.calculate_faithfulness(answer, contexts)
        relevancy = self.calculate_relevancy(question, answer)
        #precision = self.calculate_precision(contexts, question)
        recall = self.calculate_recall(contexts, answer, question)
        
        # 2. 가중치 적용하여 최종 점수 (순수 코드 계산)
        #metrics = [faithfulness, relevancy, precision, recall]
        metrics = [faithfulness, relevancy, recall]
        total_score = sum(w * m for w, m in zip(self.weights, metrics))
        
        # 3. 등급 판정
        grade_info = self._get_grade(total_score)
        
        # 4. 결과 반환
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
            'detailed_breakdown': {
                f"{name} ({weight})": f"{score} × {weight} = {round(score * weight, 3)}"
                for name, score, weight in zip(self.metric_names, metrics, self.weights)
            },
            'metric_names': self.metric_names,
        }
    
    def _get_grade(self, total_score: float) -> Dict[str, str]:
        """등급 판정 (순수 코드)"""
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


def read_csv_as_text_list(file_path: str) -> list[str]:
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        # 모든 셀을 문자열로 변환해서 한 줄씩 합침
        lines = df.astype(str).apply(lambda row: ' | '.join(row), axis=1).tolist()
        return lines
    except Exception as e:
        print(f"CSV 읽기 오류 ({file_path}): {e}")
        return []

thread_pool = ThreadPoolExecutor(max_workers=5)

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
        
def run_local_query(query_text):
    # INPUT_DIR 하드코딩 제거
    INPUT_DIR = "/Users/jy/Documents/Domain_QA_Gen/data/input/1747480728566_학교/output"
    LANCEDB_URI = f"{INPUT_DIR}/lancedb"
    
    # Load data
    entity_df = pd.read_parquet(f"{INPUT_DIR}/entities.parquet")
    community_df = pd.read_parquet(f"{INPUT_DIR}/communities.parquet")
    entities = read_indexer_entities(entity_df, community_df, 2)

    description_embedding_store = LanceDBVectorStore(collection_name="default-entity-description")
    description_embedding_store.connect(db_uri=LANCEDB_URI)

    relationship_df = pd.read_parquet(f"{INPUT_DIR}/relationships.parquet")
    relationships = read_indexer_relationships(relationship_df)

    report_df = pd.read_parquet(f"{INPUT_DIR}/community_reports.parquet")
    reports = read_indexer_reports(report_df, community_df, 2)

    text_unit_df = pd.read_parquet(f"{INPUT_DIR}/text_units.parquet")
    text_units = read_indexer_text_units(text_unit_df)

    # 모델 설정
    chat_config = LanguageModelConfig(
        api_key=GRAPHRAG_API_KEY,
        type=ModelType.OpenAIChat,
        model=GRAPHRAG_LLM_MODEL,
        max_retries=20,
    )
    chat_model = ModelManager().get_or_create_chat_model(
        name="local_search",
        model_type=ModelType.OpenAIChat,
        config=chat_config,
    )
    token_encoder = tiktoken.encoding_for_model(GRAPHRAG_LLM_MODEL)

    embedding_config = LanguageModelConfig(
        api_key=GRAPHRAG_API_KEY,
        type=ModelType.OpenAIEmbedding,
        model=GRAPHRAG_EMBEDDING_MODEL,
        max_retries=20,
    )
    text_embedder = ModelManager().get_or_create_embedding_model("local_search_embedding", ModelType.OpenAIEmbedding, config=embedding_config,)

    context_builder = LocalSearchMixedContext(
        community_reports=reports,
        text_units=text_units,
        entities=entities,
        relationships=relationships,
        entity_text_embeddings=description_embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,
        text_embedder=text_embedder,
        token_encoder=token_encoder,
    )

    search_engine = LocalSearch(
        model=chat_model,
        context_builder=context_builder,
        token_encoder=token_encoder,
        model_params={"max_tokens": 2000, "temperature": 0.0},
        context_builder_params={
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
            "max_tokens": 12000,
        },
        response_type="multiple paragraphs",
    )

    #result = thread_pool.submit(run_async, search_engine.search(query_text)).result()
    result = run_async(search_engine.search(query_text))

    # context 저장
    context_files = {}
    for key, df in result.context_data.items():
        if isinstance(df, pd.DataFrame):
            output_file = f"context_data_{key}.csv"
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            context_files[key] = output_file

    return {
        'response': result.response
    }
    
def main():
    """사용자 인터페이스"""
    print("🚀 QAGen 범용 정확도 계산기")
    print("=" * 50)
    
    load_dotenv()
    api_key = os.getenv("GRAPHRAG_API_KEY", "").strip()
    
    # 계산기 초기화
    if api_key:
        llm_evaluator = LLMEvaluator(api_key=api_key)
    else:
        print("API 키 없이 폴백 모드로 실행합니다.")
        llm_evaluator = LLMEvaluator()
    
    calculator = AccuracyCalculator(llm_evaluator)
    
    while True:
        print("\n" + "="*50)
        print("새로운 QA 평가 (종료: 'quit')")
        print("="*50)
        
        # 사용자 입력
        question = input("📝 질문: ").strip()
        if question.lower() == 'quit':
            break
        
        # answer = input("💬 답변: ").strip()
        # if answer.lower() == 'quit':
        #     break
        result = run_local_query(question)

        answer = result.get('response')
        print("서버 답변:", answer)
        
        # 컨텍스트 입력
        # print("📚 컨텍스트 (빈 줄로 종료):")
        # contexts = []
        # while True:
        #     context = input().strip()
        #     if not context:
        #         break
        #     contexts.append(context)
        # CSV 파일들 읽기 (서버가 생성했다고 가정하고, 같은 경로에 있다고 가정)
        context_files = [
            "./context_data_entities.csv",
            "./context_data_relationships.csv",
            "./context_data_reports.csv",
            "./context_data_sources.csv"
        ]
        contexts = []
        for file in context_files:
            contexts.extend(read_csv_as_text_list(file))

        # Ground truth (선택사항)
        # ground_truth = input("🎯 정답 참고 (선택사항): ").strip()
        # ground_truth = ground_truth if ground_truth else None
        #ground_truth = '. '.join(calculator._extract_key_information(answer))

        # 정확도 계산
        try:
            print("\n⏳ 계산 중...")
            result = calculator.calculate_accuracy(question, answer, contexts)
            
            # 결과 출력
            print("\n" + "🎯 평가 결과")
            print("="*30)
            print(f"최종 정확도: {result['percentage']}%")
            print(f"등급: {result['grade']} ({result['level']})")
            
            print("\n📊 세부 점수:")
            for name, score in result['metrics'].items():
                weight = result['weights'][name]
                print(f"  • {name}: {score} (가중치: {weight})")
            
            print("\n🧮 계산 과정:")
            for breakdown in result['detailed_breakdown'].values():
                print(f"  • {breakdown}")
            
            total_sum = sum(result['weights'][name] * result['metrics'][name] 
                           for name in result['metric_names'])
            print(f"  = {round(total_sum, 3)}")
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

# 테스트 실행
if __name__ == "__main__":
    # 간단한 테스트
    #print("🧪 테스트 실행")
    
    # calculator = AccuracyCalculator()  # API 키 없이 테스트
    
    # test_result = calculator.calculate_accuracy(
    #     question="파이썬에서 리스트와 튜플의 차이점은?",
    #     answer="리스트는 변경 가능하고 튜플은 변경 불가능합니다. 리스트는 []로 표현하고 튜플은 ()로 표현합니다.",
    #     contexts=["파이썬 리스트는 mutable하고 튜플은 immutable합니다.", "리스트 문법: [1,2,3], 튜플 문법: (1,2,3)"],
    #     ground_truth="리스트는 mutable, 튜플은 immutable"
    # )
    
    # print(json.dumps(test_result, ensure_ascii=False, indent=2))
    
    # print("\n" + "="*50)
    # print("실제 사용: main() 함수 실행")
    main()  # 주석 해제하여 대화형 모드 실행