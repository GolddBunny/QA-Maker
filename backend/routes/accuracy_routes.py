import os
import glob
import re
from flask import Blueprint, Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor
import asyncio
from services.accuracy_service.accuracy import AccuracyCalculator, LLMEvaluator, read_csv_as_text_list
from dotenv import load_dotenv

# 백엔드 디렉토리 경로 설정
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH_PATTERN = os.path.join(BACKEND_DIR, "*.csv")

# 멀티스레딩을 위한 스레드 풀 생성 (최대 5개 워커)
thread_pool = ThreadPoolExecutor(max_workers=5)
accuracy_bp = Blueprint('Accuracy', __name__)

load_dotenv()

api_key = os.getenv("GRAPHRAG_API_KEY")
llm_model = "gpt-4o-mini"
embedding_model = "text-embedding-3-small"

@accuracy_bp.route('/calculate-accuracy', methods=['POST'])
def calculate_accuracy_api():
    try:
        data = request.get_json()
        question = data.get("question", "")
        answer = data.get("answer", "")
        answer_type = data.get("answer_type", "local")
        page_id = data.get("page_id")

        if not question or not answer:
            return jsonify({"error": "question and answer are required"}), 400

        # CSV 파일들에서 컨텍스트 데이터 수집
        context_files = glob.glob(CSV_PATH_PATTERN)
        contexts = []
        for file in context_files:
            contexts.extend(read_csv_as_text_list(file))

        def run_accuracy():
            # LLM 평가기와 정확도 계산기 초기화
            evaluator = LLMEvaluator()
            calculator = AccuracyCalculator(evaluator)
            result = calculator.calculate_accuracy(question, answer, contexts)
            return round(result.get("percentage", 0.0), 1)  # 소수점 첫째 자리까지 반올림

        percentage = thread_pool.submit(run_accuracy).result()  # 별도 스레드에서 정확도 계산 실행

        return jsonify({
            "percentage": percentage
        })

    except Exception as e:
        print(f"서버 오류: {e}")
        return jsonify({"error": str(e)}), 500