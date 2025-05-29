import json
from pathlib import Path
import time
from flask import Blueprint, jsonify, request
from firebase_config import bucket
from datetime import datetime
from firebase_admin import storage
from datetime import datetime
import uuid

url_load_bp = Blueprint('url_load', __name__)

# URL 중복 검사 함수
def check_url_exists(page_id, url_to_check, url_type="general"):
    """Firebase Storage에서 URL 중복 검사"""
    prefix = f"pages/{page_id}/urls/"
    blobs = bucket.list_blobs(prefix=prefix)
    
    for blob in blobs:
        blob.reload()
        metadata = blob.metadata or {}
        existing_url = metadata.get('url')
        existing_type = metadata.get('type', 'general')
        
        # URL과 타입이 모두 일치하면 중복
        if existing_url == url_to_check and existing_type == url_type:
            return True
    return False

# 배치 중복 검사 함수 (성능 최적화)
def get_existing_urls(page_id, url_type="general"):
    """페이지의 기존 URL 목록을 한 번에 가져와서 성능 최적화"""
    prefix = f"pages/{page_id}/urls/"
    blobs = bucket.list_blobs(prefix=prefix)
    existing_urls = set()
    
    for blob in blobs:
        blob.reload()
        metadata = blob.metadata or {}
        existing_url = metadata.get('url')
        existing_type = metadata.get('type', 'general')
        
        if existing_url and existing_type == url_type:
            existing_urls.add(existing_url)
    
    return existing_urls

# 배치 URL 저장 함수
def save_urls_batch(page_id, urls, url_type="crawled"):
    """여러 URL을 배치로 저장 (중복 검사 포함)"""
    if not urls:
        return 0
    
    # 기존 URL 목록 한 번에 가져오기
    existing_urls = get_existing_urls(page_id, url_type)
    saved_count = 0
    
    bucket_storage = storage.bucket()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    for url in urls:
        # 중복 검사
        if url in existing_urls:
            print(f"URL 중복으로 저장 생략: {url}")
            continue
        
        # 새 URL 저장
        uuid_name = f"{uuid.uuid4().hex}.txt"
        upload_path = f"pages/{page_id}/urls/{uuid_name}"
        
        blob = bucket_storage.blob(upload_path)
        blob.metadata = {
            "url": url,
            "date": today_str,
            "root": "false",
            "type": url_type
        }
        blob.upload_from_string(url, content_type='text/plain')
        blob.make_public()
        
        # 메모리 상 기존 URL 목록에도 추가 (같은 배치 내 중복 방지)
        existing_urls.add(url)
        saved_count += 1
        
        if saved_count % 10 == 0:  # 10개마다 로그 출력
            print(f"배치 저장 진행: {saved_count}개 완료")
    
    print(f"배치 URL 저장 완료: {saved_count}개 저장, {len(urls) - saved_count}개 중복 생략")
    return saved_count

# root url 저장
def save_url_to_firebase(page_id, url):
    """Firebase Storage에 URL을 텍스트 파일로 저장 (중복 검사 포함)"""
    # 중복 검사
    if check_url_exists(page_id, url, "general"):
        print(f"URL 중복으로 저장 생략: {url}")
        return False
    
    bucket = storage.bucket()
    today_str = datetime.now().strftime('%Y-%m-%d')
    uuid_name = f"{uuid.uuid4().hex}.txt"
    upload_path = f"pages/{page_id}/urls/{uuid_name}"

    blob = bucket.blob(upload_path)
    blob.metadata = {
        "url": url,
        "date": today_str,
        "root": "true",
        "type": "general"  # 타입 추가
    }
    blob.upload_from_string(url, content_type='text/plain')
    blob.make_public()
    print(f"URL 저장 완료: {url} → {upload_path}")
    return True

# 크롤링해온 문서 url 저장 (문서 URL 구분)
def save_document_url_to_firebase(page_id, url):
    """Firebase Storage에 문서 URL을 텍스트 파일로 저장 (중복 검사 포함)"""
    # 중복 검사
    if check_url_exists(page_id, url, "document"):
        print(f"문서 URL 중복으로 저장 생략: {url}")
        return False
        
    bucket = storage.bucket()
    today_str = datetime.now().strftime('%Y-%m-%d')
    uuid_name = f"{uuid.uuid4().hex}.txt"
    upload_path = f"pages/{page_id}/urls/{uuid_name}"

    blob = bucket.blob(upload_path)
    blob.metadata = {
        "url": url,
        "date": today_str,
        "root": "false",
        "type": "document"  # 문서 URL임을 표시
    }
    blob.upload_from_string(url, content_type='text/plain')
    blob.make_public()
    print(f"크롤링 해온 문서 URL 저장 완료: {url} → {upload_path}")
    return True

# 크롤링해온 url 저장
def save_crawling_url_to_firebase(page_id, url):
    """Firebase Storage에 URL을 텍스트 파일로 저장 (중복 검사 포함)"""
    # 중복 검사
    if check_url_exists(page_id, url, "crawled"):
        print(f"크롤링 URL 중복으로 저장 생략: {url}")
        return False
        
    bucket = storage.bucket()
    today_str = datetime.now().strftime('%Y-%m-%d')
    uuid_name = f"{uuid.uuid4().hex}.txt"
    upload_path = f"pages/{page_id}/urls/{uuid_name}"

    blob = bucket.blob(upload_path)
    blob.metadata = {
        "url": url,
        "date": today_str,
        "root": "false",
        "type": "crawled"  # 타입 추가
    }
    blob.upload_from_string(url, content_type='text/plain')
    blob.make_public()
    print(f"크롤링 해온 URL 저장 완료: {url} → {upload_path}")
    return True

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

# 문서 url 목록 가져오기
def get_document_urls_from_firebase(page_id):
    prefix = f"pages/{page_id}/urls/"
    blobs = bucket.list_blobs(prefix=prefix)
    urls = []

    for blob in blobs:
        blob.reload()
        metadata = blob.metadata or {}
        url = metadata.get('url')
        date = metadata.get('date', blob.time_created.strftime('%Y-%m-%d'))
        url_type = metadata.get('type', '')
        
        # 문서 URL만 필터링
        if url and url_type == 'document':
            urls.append({
                'url': url,
                'date': date
            })
    urls.sort(key=lambda x: x['date'], reverse=True)
    return urls

# root url 목록 가져오기
def get_root_urls_from_firebase(page_id):
    prefix = f"pages/{page_id}/urls/"
    blobs = bucket.list_blobs(prefix=prefix)
    urls = []

    for blob in blobs:
        blob.reload()
        metadata = blob.metadata or {}
        url = metadata.get('url')
        date = metadata.get('date', blob.time_created.strftime('%Y-%m-%d'))
        if metadata.get('root') == 'true':
            urls.append({
                'url': url,
                'date': date
            })
    urls.sort(key=lambda x: x['date'], reverse=True)
    return urls

#url 추가
@url_load_bp.route('/add-url/<page_id>', methods=['POST'])
def add_url(page_id):
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({"success": False, "error": "입력된 URL이 없습니다."}), 400
        
        # 1. URL 저장 (중복 검사 포함)
        is_saved = save_url_to_firebase(page_id, url)

        # 2. 저장된 URL 목록 조회
        saved_urls = get_urls_from_firebase(page_id)

        if is_saved:
            message = "URL 저장 완료"
        else:
            message = "URL이 이미 존재합니다"

        return jsonify({
            "success": True,
            "message": message,
            "urls": saved_urls,
            "is_duplicate": not is_saved
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"URL 저장 중 오류 발생: {str(e)}"}), 500

#url 목록 불러오기
@url_load_bp.route('/get-urls/<page_id>', methods=['GET'])
def get_saved_urls(page_id):
    urls = get_urls_from_firebase(page_id)
    if urls:
        print(f"Firebase에서 가져온 URL 목록 ({page_id}): {urls}")
        return jsonify({"success": True, "urls": urls}), 200
    else:
        return jsonify({"success": False, "error": "URL 조회 중 오류 발생"}), 500

#문서 url 목록 불러오기
@url_load_bp.route('/get-document-urls/<page_id>', methods=['GET'])
def get_saved_document_urls(page_id):
    urls = get_document_urls_from_firebase(page_id)
    if urls:
        print(f"Firebase에서 가져온 문서 URL 목록 ({page_id}): {urls}")
        return jsonify({"success": True, "urls": urls}), 200
    else:
        return jsonify({"success": True, "urls": []}), 200  # 빈 목록도 성공으로 처리
