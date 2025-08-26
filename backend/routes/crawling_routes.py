import time
from flask import Blueprint, jsonify, request
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from services.crawling_service.urlCrawling import main as crawl_urls
from routes.urlLoad_routes import get_root_urls_from_firebase, save_crawling_url_to_firebase, get_urls_from_firebase, save_document_url_to_firebase, save_urls_batch
from services.crawling_service.crawling_and_structuring import main as crawling_and_structuring
from firebase_admin import firestore
from services.crawling_service import line1

crawling_bp = Blueprint('crawling', __name__)

# Firestore 클라이언트
db = firestore.client()

#url 크롤링 시작
@crawling_bp.route('/start-crawling/<page_id>', methods=['POST'])
def start_url_crawling(page_id):
    """저장된 URL들을 가져와서 크롤링 시작"""
    try:
        print(f"URL 크롤링 시작: {page_id}")
        start_time = time.time()
        
        # 1. Firebase에서 저장된 URL들 가져오기
        saved_urls = get_root_urls_from_firebase(page_id)
        print(f"Firebase에서 가져온 root URL 개수: {len(saved_urls) if saved_urls else 0}")

        # 가져온 URL 리스트 출력
        if saved_urls:
            for i, url_info in enumerate(saved_urls):
                print(f"   {i+1}. {url_info.get('url', 'N/A')} (날짜: {url_info.get('date', 'N/A')})")

        # URL이 없는 경우 에러 반환
        if not saved_urls:
            return jsonify({"success": False, "error": "크롤링할 URL이 없습니다. 먼저 URL을 추가해주세요."}), 400
        
        # 2. for문으로 saved_urls 순회하며 크롤링
        for url in saved_urls:
            start_url = url['url']
            print(f"URL 크롤링 실행 중: {start_url}")

            # 3. url 크롤링 실행            
            crawling_results = crawl_urls(
                start_url=start_url,
            )
            
            # 크롤링 결과 확인
            if crawling_results and "error" not in crawling_results:
                print(f"URL 크롤링 성공: {len(crawling_results.get('page_urls', []))}개 페이지 발견")
                
                # 4. 결과 정보를 딕셔너리로 정리
                results_info = {
                    "page_id": page_id,
                    "start_url": start_url,
                    "base_domain": crawling_results.get('base_domain', ''),
                    "scope_patterns": crawling_results.get('scope_patterns', []),
                    "total_pages": crawling_results.get('total_pages_discovered', 0),
                    "total_documents": crawling_results.get('total_documents_discovered', 0),
                    "results_dir": crawling_results.get('results_dir', ''),
                    "execution_time": crawling_results.get('execution_time', 0),
                    "timestamp": datetime.now().isoformat()
                }

                # page_urls에서 URL 목록을 가져와서 Firebase에 저장 (배치 처리)
                page_urls = crawling_results.get('page_urls', [])
                saved_count = save_urls_batch(page_id, page_urls, "crawled")
                
                # doc_urls에서 문서 URL 목록을 가져와서 Firebase에 저장 (배치 처리)
                doc_urls = crawling_results.get('doc_urls', [])
                doc_saved_count = save_urls_batch(page_id, doc_urls, "document")
                
                print(f"Firebase에 {saved_count}개 페이지 URL, {doc_saved_count}개 문서 URL 저장 완료")
                print(f"발견된 문서 URL: {crawling_results.get('total_documents_discovered', 0)}개")
                print(f"Firebase에 {saved_count}개 URL 저장 완료")

                # 크롤링 완료 응답 반환
                end_time = time.time()
                execution_time = round(end_time - start_time)
                return jsonify({
                    "success": True,
                    "message": "URL 크롤링 완료",
                    "results": results_info,
                    'execution_time': execution_time
                }), 200
            else:
                print(f"URL 크롤링 실패: {crawling_results.get('error', '알 수 없는 오류')}")
                return jsonify({
                    "success": False, 
                    "error": f"크롤링 실패: {crawling_results.get('error', '알 수 없는 오류')}"
                }), 500
            
    except Exception as e:
        print(f"URL 크롤링 중 오류: {str(e)}")
        return jsonify({"success": False, "error": f"크롤링 중 오류 발생: {str(e)}"}), 500

# 웹 크롤링 및 구조화
@crawling_bp.route('/crawl-and-structure/<page_id>', methods=['POST'])
def crawl_and_structure(page_id):
    """웹 크롤링 및 구조화 시작 (crawling_and_structuring.py)"""
    try:
        print(f"crawling_routes.py: 웹 크롤링 및 구조화 시작: {page_id}")
        start_time = time.time()
        # 1. Firebase에서 저장된 URL들 가져오기
        saved_urls = get_urls_from_firebase(page_id)
        
        if not saved_urls:
            print(f"crawling_routes.py: 크롤링할 URL이 없습니다.")
            return jsonify({"success": False, "error": "크롤링할 URL이 없습니다. 먼저 URL 크롤링을 실행해주세요."}), 400
        
        print(f"crawling_routes.py: 크롤링할 URL 개수: {len(saved_urls)}")
        
        # 2. URL 리스트를 crawling_and_structuring 함수에 전달
        result = crawling_and_structuring(page_id, saved_urls)
        end_time = time.time()
        execution_time = round(end_time - start_time)

        # 성공 여부 확인
        if result and result.get('success', False):
            return jsonify({
                "success": True,
                "message": "웹 크롤링 및 구조화 완료",
                "results": result.get('results', {}),
                'execution_time': execution_time
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"웹 크롤링 실패: {result.get('error', '알 수 없는 오류')}"
            }), 500
            
    except Exception as e:
        print(f"웹 크롤링 중 오류: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"웹 크롤링 중 오류 발생: {str(e)}"
        }), 500

# 텍스트 파일 정리
@crawling_bp.route('/line1/<page_id>', methods=['POST'])
def cleanup_text_files(page_id):
    """텍스트 파일 정리 (line1.py)"""
    try:
        print(f"텍스트 정리 시작: {page_id}")
        start_time = time.time()

        # URL 입력 경로 계산 
        url_base_path = Path(f"../data/input/{page_id}_url")
        url_input_path = url_base_path / "input"
        
        # 경로 존재 확인
        if not url_input_path.exists():
            return jsonify({
                "success": False,
                "error": f"URL 입력 경로를 찾을 수 없습니다: {url_input_path.resolve()}"
            }), 400
        
        print(f"텍스트 정리 대상 경로: {url_input_path.resolve()}")
        
        # line1 모듈의 main 함수 실행 
        abs_url_input_path = str(url_input_path.resolve())
        result = line1.main(abs_url_input_path, page_id)
        end_time = time.time()
        execution_time = round(end_time - start_time)

        #결과 반환
        if result.get("success", False):
            return jsonify({
                "success": True,
                "message": "텍스트 정리 완료",
                "results": result,
                'execution_time': execution_time
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"텍스트 정리 실패: {result.get('error', '알 수 없는 오류')}"
            }), 500
            
    except Exception as e:
        print(f"텍스트 정리 중 오류: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"텍스트 정리 중 오류 발생: {str(e)}"
        }), 500


# @crawling_bp.route('/get-crawling-status/<page_id>', methods=['GET'])
# def get_crawling_status(page_id):
#     """크롤링 상태 확인"""
#     try:
#         # 데이터 디렉토리에서 크롤링 결과 확인
#         url_base_path = f'../data/input/{page_id}_url'  
#         url_input_path = os.path.join(url_base_path, 'input')
        