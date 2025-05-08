from flask import Blueprint, jsonify, request
import time
from utils.crawling import crawl_main
from backend.utils.past.url_manager import URLManager

crawling_bp = Blueprint('crawling', __name__)
url_manager = URLManager()

@crawling_bp.route('/add-url/<page_id>', methods=['POST'])
def add_url(page_id):
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({"success": False, "error": "입력된 URL이 없습니다."}), 400
        
        # 1. URL 저장
        saved_urls = url_manager.add_url(page_id, url)
        print(f"페이지 '{page_id}'에 URL이 성공적으로 저장되었습니다: {url}")
        
        # 2. 크롤링 실행
        print(f"크롤링 시작: {url}")
        start_time = time.time()
        
        try:
            saved_files, saved_attachments = crawl_main(url)
            
            crawl_result = {
                "url": url,
                "status": "success",
                "saved_files": len(saved_files),
                "saved_attachments": len(saved_attachments)
            }
            
        except Exception as e:
            crawl_result = {
                "url": url,
                "status": "error",
                "error": str(e)
            }
        
        execution_time = time.time() - start_time
        print(f"크롤링 완료. 총 실행 시간: {execution_time}초")
        
        return jsonify({
            "success": True,
            "message": "URL 저장 및 크롤링 완료",
            "urls": saved_urls,
            "crawl_result": crawl_result,
            "execution_time": execution_time
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": f"URL 저장 및 크롤링 중 오류 발생: {str(e)}"}), 500

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