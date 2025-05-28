from flask import Blueprint, jsonify, request
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from services.crawling_service.urlCrawling import main as crawl_urls
from urlLoad_routes import get_root_urls_from_firebase, save_crawling_url_to_firebase

crawling_bp = Blueprint('crawling', __name__)

# 경로 설정
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
crawling_service_dir = backend_dir / "services" / "crawling_service"
sys.path.append(str(crawling_service_dir))

#url 크롤링 시작
@crawling_bp.route('/start-crawling/<page_id>', methods=['POST'])
def start_url_crawling(page_id):
    """저장된 URL들을 가져와서 크롤링 시작"""
    try:
        # 1. Firebase에서 저장된 URL들 가져오기
        saved_urls = get_root_urls_from_firebase(page_id)
        
        if not saved_urls:
            return jsonify({"success": False, "error": "크롤링할 URL이 없습니다."}), 400
        
        # 2. for문으로 saved_urls 순회하며 크롤링
        for url in saved_urls:
            start_url = url['url']

            # 3. url 크롤링 실행            
            crawling_results = crawl_urls(
                start_url=start_url,
            )
            #TODO: URL/문서 리스트 배열로 받아서 firebase에 저장해야 함.
            json_data = crawling_results.get('json_data', {})

            #TODO: url/문서 크롤링 log에 찍힐 때마다, ui에서도 도로록도로록 숫자 증가하도록 해야함. -> firebase에 length만 실시간으로 증가하도록 처리
            if crawling_results and "error" not in crawling_results:
                # 4. url 크롤링 결과를 Firebase에 저장
                
                results_info = {
                    "page_id": page_id,
                    "start_url": start_url,
                    "base_domain": json_data.get('base_domain', ''),
                    "scope_patterns": json_data.get('scope_patterns', []),
                    "total_pages": json_data.get('total_pages_discovered', 0),
                    "total_documents": json_data.get('total_documents_discovered', 0),
                    "results_dir": json_data.get('results_dir', ''),
                    "execution_time": json_data.get('execution_time_seconds', 0),
                    "timestamp": datetime.now().isoformat()
                }


                for url in json_data.get('page_urls', []):
                    save_crawling_url_to_firebase(page_id, url)
            
            return jsonify({
                "success": True,
                "message": "URL 크롤링 완료",
                "results": results_info
            }), 200
        else:
            return jsonify({
                "success": False, 
                "error": f"크롤링 실패: {crawling_results.get('error', '알 수 없는 오류')}"
            }), 500
            
    except Exception as e:
        print(f"URL 크롤링 중 오류: {str(e)}")
        return jsonify({"success": False, "error": f"크롤링 중 오류 발생: {str(e)}"}), 500

@crawling_bp.route('/start-structuring/<page_id>', methods=['POST'])
def start_web_structuring(page_id):
    """웹 크롤링 및 구조화 시작 (crawling_and_structuring.py)"""
    try:
        print(f"🔄 웹 크롤링 및 구조화 시작: {page_id}")
        
        # crawling_and_structuring.py 실행
        script_path = crawling_service_dir / "crawling_and_structuring.py"
        
        # 데이터 디렉토리에서 최신 크롤링 결과 찾기
        data_dir = backend_dir.parent / "data" / "crawling"
        
        # 가장 최근 크롤링 폴더 찾기
        crawling_folders = [d for d in data_dir.iterdir() if d.is_dir()]
        if not crawling_folders:
            return jsonify({
                "success": False, 
                "error": "크롤링 결과 폴더를 찾을 수 없습니다."
            }), 400
        
        # 가장 최근 폴더 선택 (이름 기준 정렬)
        latest_folder = sorted(crawling_folders, key=lambda x: x.name)[-1]
        url_file = latest_folder / f"page_urls_{latest_folder.name.split('_')[1]}.txt"
        
        if not url_file.exists():
            return jsonify({
                "success": False, 
                "error": f"URL 파일을 찾을 수 없습니다: {url_file}"
            }), 400
        
        # Python 스크립트 실행
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, cwd=str(crawling_service_dir))
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": "웹 크롤링 및 구조화 완료",
                "results": {
                    "url_file": str(url_file),
                    "output_dir": str(latest_folder),
                    "stdout": result.stdout
                }
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"웹 크롤링 실패: {result.stderr}"
            }), 500
            
    except Exception as e:
        print(f"웹 크롤링 중 오류: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"웹 크롤링 중 오류 발생: {str(e)}"
        }), 500

@crawling_bp.route('/cleanup-text/<page_id>', methods=['POST'])
def cleanup_text_files(page_id):
    """텍스트 파일 정리 (line1.py)"""
    try:
        print(f"🧹 텍스트 정리 시작: {page_id}")
        
        # line1.py 실행
        script_path = crawling_service_dir / "line1.py"
        
        # Python 스크립트 실행
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, cwd=str(crawling_service_dir))
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": "텍스트 정리 완료",
                "results": {
                    "stdout": result.stdout
                }
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"텍스트 정리 실패: {result.stderr}"
            }), 500
            
    except Exception as e:
        print(f"텍스트 정리 중 오류: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"텍스트 정리 중 오류 발생: {str(e)}"
        }), 500

@crawling_bp.route('/get-crawling-status/<page_id>', methods=['GET'])
def get_crawling_status(page_id):
    """크롤링 상태 확인"""
    try:
        # 데이터 디렉토리에서 크롤링 결과 확인
        data_dir = backend_dir.parent / "data" / "crawling"
        
        crawling_folders = [d for d in data_dir.iterdir() if d.is_dir()]
        
        if crawling_folders:
            latest_folder = sorted(crawling_folders, key=lambda x: x.name)[-1]
            
            # URL 파일과 크롤링 결과 파일들 확인
            url_files = list(latest_folder.glob("page_urls_*.txt"))
            jina_files = list(latest_folder.glob("**/jina_crawling/*.txt"))
            
            return jsonify({
                "success": True,
                "status": {
                    "latest_folder": str(latest_folder),
                    "url_files_count": len(url_files),
                    "jina_files_count": len(jina_files),
                    "has_results": len(jina_files) > 0
                }
            }), 200
        else:
            return jsonify({
                "success": True,
                "status": {
                    "latest_folder": None,
                    "url_files_count": 0,
                    "jina_files_count": 0,
                    "has_results": False
                }
            }), 200
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": f"상태 확인 중 오류: {str(e)}"
        }), 500 