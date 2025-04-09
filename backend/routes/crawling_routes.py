import time
from flask import Blueprint, jsonify, request
from backend.utils.crawling import crawl_main
from backend.utils.url_manager import URLManager

crawling_bp = Blueprint('crawling', __name__)
url_manager = URLManager()

@crawling_bp.route('/crawling', methods=['POST'])
def crawling():
    try:
        data = request.json
        urls = data.get('urls', [])
        max_pages = data.get('max_pages', 1)
        
        if not urls:
            return jsonify({"status": "error", "message": "입력된 URL이 없습니다."}), 400
        
        # 1. URL 저장
        saved_urls = url_manager.add_urls(urls)
        print(f"URL이 성공적으로 저장되었습니다: {saved_urls}")
        
        # 2. 크롤링 실행
        print(f"크롤링 시작: {urls}")
        start_time = time.time()
        crawled_urls = []
        crawl_results = []
        
        for url in urls:
            try:
                saved_files, saved_attachments = crawl_main(url, max_pages=max_pages)
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
            "status": "success", 
            "message": "URL 저장 및 크롤링 완료", 
            "urls": saved_urls,
            "crawled_urls": crawled_urls, 
            "crawl_results": crawl_results,
            "execution_time": execution_time
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"URL 저장 및 크롤링 중 오류 발생: {str(e)}"}), 500
