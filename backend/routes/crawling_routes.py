import time
from flask import Blueprint, jsonify, request
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from services.crawling_service.urlCrawling import main as crawl_urls
from routes.urlLoad_routes import get_general_urls_from_firebase, get_urls_from_firebase, save_url_to_firebase, save_urls_batch
from services.crawling_service.crawling_and_structuring import main as crawling_and_structuring
from firebase_admin import firestore
# from services.crawling_service import line1
from urllib.parse import urlparse
from services.execution_time_service import get_tracker

crawling_bp = Blueprint('crawling', __name__)

# Firestore 클라이언트
db = firestore.client()

#url 크롤링 시작
@crawling_bp.route('/start-crawling/<page_id>', methods=['POST'])
def start_url_crawling(page_id):
    """저장된 URL들을 가져와서 크롤링 시작"""
    
    # 실행 시간 트래커 시작
    tracker = get_tracker(page_id)
    
    try:
        start_time = time.time()
        
        # 1. Firebase에서 저장된 URL들 가져오기
        saved_urls = get_general_urls_from_firebase(page_id)
        
        print(f"📋 Firebase에서 가져온 일반 URL 개수: {len(saved_urls) if saved_urls else 0}")
        if saved_urls:
            for i, url_info in enumerate(saved_urls):
                print(f"   {i+1}. {url_info.get('url', 'N/A')} (날짜: {url_info.get('date', 'N/A')})")
        
        if not saved_urls:
            return jsonify({"success": False, "error": "크롤링할 URL이 없습니다. 먼저 URL을 추가해주세요."}), 400

        # 2. for문으로 saved_urls 순회하며 크롤링
        for url in saved_urls:
            start_url = url['url']
            print(f"🔍 URL 크롤링 실행 중: {start_url}")

            # URL에서 자동으로 scope 패턴 추출
            parsed_url = urlparse(start_url)
            path_parts = [part for part in parsed_url.path.split('/') if part and part != 'index.do']
            
            # 범용적인 scope 패턴 추출 룰
            scope_patterns = []
            
            # 제외할 파일 확장자 목록
            exclude_extensions = ['.do', '.jsp', '.php', '.html', '.htm', '.asp', '.aspx', '.action']
            
            # 제외할 일반적인 웹사이트 경로
            exclude_paths = ['web', 'www', 'sites', 'admin', 'common', 'include', 'images', 'css', 'js', 'static']
            
            for part in path_parts:
                # 1. 파일 확장자가 있는 경우 제외
                has_extension = any(part.lower().endswith(ext) for ext in exclude_extensions)
                if has_extension:
                    continue
                    
                # 2. 일반적인 웹사이트 경로 제외
                if part.lower() in exclude_paths:
                    continue
                    
                # 3. 너무 짧은 경로 제외 (1-2글자)
                if len(part) <= 2:
                    continue
                    
                # 4. 순수 숫자로만 구성된 경우 - ID로 간주하여 선택적 포함
                if part.isdigit():
                    # 4자리 이상의 숫자는 의미있는 ID로 간주 (예: 10727)
                    if len(part) >= 4:
                        scope_patterns.append(part)
                    continue
                
                # 5. 의미있는 디렉토리명 추가
                scope_patterns.append(part)
            
            # 로깅
            if scope_patterns:
                print(f"🎯 자동 추출된 범위 패턴: {scope_patterns}")
            else:
                print("🌐 범위 패턴 없음 - 도메인 전체 크롤링")

            # 3. url 크롤링 실행            
            crawling_results = crawl_urls(
                start_url=start_url,
                scope=scope_patterns if scope_patterns else None
            )
            
            # crawling_results는 직접 결과 딕셔너리입니다
            if crawling_results and "error" not in crawling_results:
                print(f"✅ URL 크롤링 성공: {len(crawling_results.get('page_urls', []))}개 페이지 발견")
                
                # 4. url 크롤링 결과를 Firebase에 저장
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
                # set 객체인 경우 list로 변환 (오류 방지)
                if isinstance(page_urls, set):
                    page_urls = list(page_urls)
                saved_count = save_urls_batch(page_id, page_urls, "crawled")
                
                # doc_urls에서 문서 URL 목록을 가져와서 Firebase에 저장 (배치 처리)
                doc_urls = crawling_results.get('doc_urls', [])
                # set 객체인 경우 list로 변환 (오류 방지)
                if isinstance(doc_urls, set):
                    doc_urls = list(doc_urls)
                doc_saved_count = save_urls_batch(page_id, doc_urls, "document")
                
                print(f"💾 Firebase에 {saved_count}개 페이지 URL, {doc_saved_count}개 문서 URL 저장 완료")
                print(f"📎 발견된 문서 URL: {crawling_results.get('total_documents_discovered', 0)}개")
            
                print(f"💾 Firebase에 {saved_count}개 URL 저장 완료")
                end_time = time.time()
                execution_time = round(end_time - start_time)
                
                # 실행 시간 트래커에 기록
                additional_data = {
                    "start_url": start_url,
                    "total_pages_discovered": crawling_results.get('total_pages_discovered', 0),
                    "total_documents_discovered": crawling_results.get('total_documents_discovered', 0),
                    "scope_patterns": scope_patterns,
                    "saved_pages": saved_count,
                    "saved_documents": doc_saved_count
                }
                tracker.record_step('url_crawling', execution_time, additional_data)
                
                return jsonify({
                    "success": True,
                    "message": "URL 크롤링 완료",
                    "results": results_info,
                    'execution_time': execution_time
                }), 200
            else:
                print(f"❌ URL 크롤링 실패: {crawling_results.get('error', '알 수 없는 오류')}")
                return jsonify({
                    "success": False, 
                    "error": f"크롤링 실패: {crawling_results.get('error', '알 수 없는 오류')}"
                }), 500
            
    except Exception as e:
        print(f"URL 크롤링 중 오류: {str(e)}")
        return jsonify({"success": False, "error": f"크롤링 중 오류 발생: {str(e)}"}), 500

@crawling_bp.route('/crawl-and-structure/<page_id>', methods=['POST'])
def crawl_and_structure(page_id):
    """웹 크롤링 및 구조화 시작 (crawling_and_structuring.py)"""
    
    # 실행 시간 트래커 가져오기
    tracker = get_tracker(page_id)
    
    try:
        print(f"crawling_routes.py: 🔄 웹 크롤링 및 구조화 시작: {page_id}")
        start_time = time.time()
        # 1. Firebase에서 저장된 URL들 가져오기 (크롤링된 모든 URL)
        saved_urls = get_urls_from_firebase(page_id)
        
        if not saved_urls:
            print(f"crawling_routes.py: 🔄 크롤링할 URL이 없습니다.")
            return jsonify({"success": False, "error": "크롤링할 URL이 없습니다. 먼저 URL 크롤링을 실행해주세요."}), 400
        
        print(f"crawling_routes.py: 🔄 크롤링할 URL 개수: {len(saved_urls)}")
        
        # 2. URL 리스트를 crawling_and_structuring 함수에 전달
        result = crawling_and_structuring(page_id, saved_urls)
        end_time = time.time()
        execution_time = round(end_time - start_time)
        
        # 실행 시간 트래커에 기록
        additional_data = {
            "processed_urls": len(saved_urls),
            "result_success": result.get('success', False) if result else False
        }
        if result and result.get('results'):
            additional_data.update(result.get('results', {}))
        
        tracker.record_step('web_structuring', execution_time, additional_data)
        
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

