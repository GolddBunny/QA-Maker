import json
import time
from flask import Blueprint, jsonify, request
from utils.url_manager import URLManager
from firebase_config import bucket
from datetime import datetime
from firebase_admin import storage
from datetime import datetime
import uuid

from utils.crawling import crawl_main

url_load_bp = Blueprint('url_load', __name__)
url_manager = URLManager()

#url 저장
def save_url_to_firebase(page_id, url):
    """Firebase Storage에 URL을 텍스트 파일로 저장"""
    bucket = storage.bucket()
    today_str = datetime.now().strftime('%Y-%m-%d')
    uuid_name = f"{uuid.uuid4().hex}.txt"
    upload_path = f"pages/{page_id}/urls/{uuid_name}"

    blob = bucket.blob(upload_path)
    blob.metadata = {
        "url": url,
        "date": today_str
    }
    blob.upload_from_string(url, content_type='text/plain')
    blob.make_public()
    print(f"URL 저장 완료: {url} → {upload_path}")

#url 모든 목록 가져오기
def get_urls_from_firebase(page_id):
    prefix = f"pages/{page_id}/urls/"
    blobs = bucket.list_blobs(prefix=prefix)
    urls = []

    for blob in blobs:
        blob.reload()  # 메타데이터 최신화
        metadata = blob.metadata or {}
        url = metadata.get('url')
        date = metadata.get('date', blob.time_created.strftime('%Y-%m-%d'))

        if url:
            urls.append({
                'url': url,
                'date': date
            })
    urls.sort(key=lambda x: x['date'], reverse=True)
    return urls

@url_load_bp.route('/add-url/<page_id>', methods=['POST'])
def add_url(page_id):
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({"success": False, "error": "입력된 URL이 없습니다."}), 400
        
        # 1. URL 저장
        save_url_to_firebase(page_id, url)

        # 2. 저장된 URL 목록 조회
        saved_urls = get_urls_from_firebase(page_id)

        return jsonify({
            "success": True,
            "message": "URL 저장 완료",
            "urls": saved_urls
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"URL 저장 중 오류 발생: {str(e)}"}), 500

#url 목록 불러오기
@url_load_bp.route('/get-urls/<page_id>', methods=['GET'])
def get_saved_urls(page_id):
    try:
        urls = get_urls_from_firebase(page_id)
        print(f"[get-urls] page_id: {page_id}, URL 수: {len(urls)}")
        return jsonify({"success": True, "urls": urls}), 200
    except Exception as e:
        print(f"[get-urls 오류] page_id: {page_id}, 에러: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
# 없애도 되는 코드인가?
@url_load_bp.route('/get-all-page-ids', methods=['GET'])
def get_all_page_ids():
    try:
        page_ids = url_manager.get_all_page_ids()
        print(f"저장된 모든 페이지 ID 목록: {page_ids}")
        return jsonify({"success": True, "page_ids": page_ids}), 200
    except Exception as e:
        print(f"페이지 ID 조회 중 오류 발생: {str(e)}")
        return jsonify({"success": False, "error": f"페이지 ID 조회 중 오류 발생: {str(e)}"}), 500