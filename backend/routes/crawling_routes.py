import os
from flask import Blueprint, jsonify, request
import time
from routes.page_routes import ensure_page_directory
from utils.crawling import crawl_main
from utils.url_manager import URLManager

crawling_bp = Blueprint('crawling', __name__)
url_manager = URLManager()



@crawling_bp.route('/crawling/<page_id>', methods=['POST'])
def crawling(page_id):
    try:
        # 저장된 URL 조회
        urls = url_manager.load_urls(page_id)
        
        if not urls:
            return jsonify({"success": False, "error": f"페이지 '{page_id}'에 저장된 URL이 없습니다."}), 400
        
        # 크롤링 실행
        print(f"페이지 '{page_id}'의 URL 크롤링 시작: {urls}")
        start_time = time.time()
        crawled_urls = []
        crawl_results = []
        
        for url in urls:
            try:
                saved_files, saved_attachments = crawl_main(url)
                crawled_urls.append(url)
                crawl_results.append({
                    "url": url,
                    "status": "success",
                    "saved_files": len(saved_files),
                    "saved_attachments": len(saved_attachments)
                })
            except Exception as e:
                crawl_results.append({
                    "url": url,
                    "status": "error",
                    "error": str(e)
                })
        
        execution_time = time.time() - start_time
        print(f"크롤링 완료. 총 실행 시간: {execution_time}초")
        
        return jsonify({
            "success": True,
            "message": f"페이지 '{page_id}'의 URL 크롤링 완료",
            "urls": urls,
            "crawled_urls": crawled_urls,
            "crawl_results": crawl_results,
            "execution_time": execution_time
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": f"URL 크롤링 중 오류 발생: {str(e)}"}), 500
    
@crawling_bp.route('/crawling/content/<page_id>', methods=['GET'])
def get_crawled_content(page_id):
    """크롤링된 URL 내용 가져오기"""
    try:
        base_path, input_path, _ = ensure_page_directory(page_id)
        
        # 크롤링된 텍스트 파일들을 읽어 내용 반환
        crawled_content = ""
        
        for file_name in os.listdir(input_path):
            if file_name.endswith(".txt") and "crawled_" in file_name:
                file_path = os.path.join(input_path, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    crawled_content += f"--- {file_name} ---\n"
                    crawled_content += file.read() + "\n\n"
        
        return crawled_content
    
    except Exception as e:
        return jsonify({"success": False, "error": f"크롤링된 내용 가져오기 실패: {str(e)}"}), 500