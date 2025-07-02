from flask import Blueprint, jsonify, request
from datetime import datetime
from firebase_admin import firestore

url_load_bp = Blueprint('url_load', __name__)

# Firestore 클라이언트
db = firestore.client()

# URL 중복 검사 함수 (Firestore 버전)
def check_url_exists(page_id, url_to_check, url_type="general"):
    """Firestore에서 URL 중복 검사"""
    urls_ref = db.collection('urls')
    query = urls_ref.where('page_id', '==', page_id).where('url', '==', url_to_check).where('type', '==', url_type)
    docs = query.get()
    return len(docs) > 0

# 배치 중복 검사 함수 (Firestore 버전)
def get_existing_urls(page_id, url_type="general"):
    """페이지의 기존 URL 목록을 한 번에 가져와서 성능 최적화"""
    urls_ref = db.collection('urls')
    query = urls_ref.where('page_id', '==', page_id).where('type', '==', url_type)
    docs = query.get()
    
    existing_urls = set()
    for doc in docs:
        data = doc.to_dict()
        existing_urls.add(data.get('url'))
    
    return existing_urls

# 배치 URL 저장 함수 (Firestore 버전)
def save_urls_batch(page_id, urls, url_type="crawled"):
    """여러 URL을 배치로 저장 (중복 검사 포함)"""
    if not urls:
        return 0
    
    # 기존 URL 목록 한 번에 가져오기
    existing_urls = get_existing_urls(page_id, url_type)
    saved_count = 0
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Firestore 배치 처리 (최대 500개씩)
    batch_size = 500
    for i in range(0, len(urls), batch_size):
        batch = db.batch()
        batch_urls = urls[i:i + batch_size]
        
        for url in batch_urls:
            # 중복 검사
            if url in existing_urls:
                print(f"URL 중복으로 저장 생략: {url}")
                continue
            
            # 새 URL 저장
            doc_ref = db.collection('urls').document()
            batch.set(doc_ref, {
                "url": url,
                "page_id": page_id,
                "date": today_str,
                "type": url_type,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            
            # 메모리 상 기존 URL 목록에도 추가 (같은 배치 내 중복 방지)
            existing_urls.add(url)
            saved_count += 1
        
        # 배치 커밋
        if saved_count > 0:
            batch.commit()
            print(f"배치 저장 진행: {i + len(batch_urls)}개 처리 완료")
    
    print(f"배치 URL 저장 완료: {saved_count}개 저장, {len(urls) - saved_count}개 중복 생략")
    return saved_count

# 단일 URL 저장 함수 (Firestore 버전)
def save_url_to_firebase(page_id, url, url_type="general"):
    """Firestore에 단일 URL을 저장 (중복 검사 포함)"""
    # 중복 검사
    if check_url_exists(page_id, url, url_type):
        print(f"URL 중복으로 저장 생략: {url} (타입: {url_type})")
        return False
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    doc_ref = db.collection('urls').document()
    doc_ref.set({
        "url": url,
        "page_id": page_id,
        "date": today_str,
        "type": url_type,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    
    print(f"URL 저장 완료: {url} (타입: {url_type})")
    return True

# 범용 URL 가져오기 함수 (타입별 필터링)
def get_urls_by_type(page_id, url_type=None):
    """타입별로 URL 가져오기"""
    urls_ref = db.collection('urls')
    query = urls_ref.where('page_id', '==', page_id)
    
    if url_type:
        query = query.where('type', '==', url_type)
    
    query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)
    docs = query.get()
    
    urls = []
    for doc in docs:
        data = doc.to_dict()
        urls.append({
            'url': data.get('url'),
            'date': data.get('date'),
            'type': data.get('type')
        })
    
    return urls

# 크롤링된 URL 목록 가져오기 (Firestore 버전) - crawled 타입만
def get_urls_from_firebase(page_id):
    """크롤링된 URL만 가져오기 (type='crawled')"""
    return get_urls_by_type(page_id, 'crawled')

# general 타입 URL 목록 가져오기
def get_general_urls_from_firebase(page_id):
    """일반 URL만 가져오기 (type='general')"""
    return get_urls_by_type(page_id, 'general')

# 문서 url 목록 가져오기 (Firestore 버전)
def get_document_urls_from_firebase(page_id):
    """문서 URL만 가져오기 (type='document')"""
    return get_urls_by_type(page_id, 'document')

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

        # 2. 저장된 URL 목록 조회 (사용자가 추가한 일반 URL)
        saved_urls = get_general_urls_from_firebase(page_id)

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

# 일반 URL 목록 불러오기 (사용자가 직접 추가한 URL)
@url_load_bp.route('/get-urls/<page_id>', methods=['GET'])
def get_saved_urls(page_id):
    """사용자가 직접 추가한 URL 목록 (general 타입)"""
    urls = get_general_urls_from_firebase(page_id)
    print(f"Firestore에서 가져온 일반 URL 목록 ({page_id}): {len(urls)}개")
    return jsonify({"success": True, "urls": urls}), 200

# 크롤링된 URL 목록 불러오기
@url_load_bp.route('/get-crawled-urls/<page_id>', methods=['GET'])
def get_saved_crawled_urls(page_id):
    """크롤링된 URL 목록 (crawled 타입)"""
    urls = get_urls_from_firebase(page_id)
    print(f"Firestore에서 가져온 크롤링 URL 목록 ({page_id}): {len(urls)}개")
    return jsonify({"success": True, "urls": urls}), 200

# 문서 URL 목록 불러오기
@url_load_bp.route('/get-document-urls/<page_id>', methods=['GET'])
def get_saved_document_urls(page_id):
    """문서 URL 목록 (document 타입)"""
    urls = get_document_urls_from_firebase(page_id)
    print(f"Firestore에서 가져온 문서 URL 목록 ({page_id}): {len(urls)}개")
    return jsonify({"success": True, "urls": urls}), 200

# 모든 타입 URL 목록 불러오기
@url_load_bp.route('/get-all-urls/<page_id>', methods=['GET'])
def get_all_saved_urls(page_id):
    """모든 타입의 URL 목록"""
    urls = get_urls_by_type(page_id)  # 타입 필터 없이 모든 URL
    print(f"Firestore에서 가져온 전체 URL 목록 ({page_id}): {len(urls)}개")
    return jsonify({"success": True, "urls": urls}), 200
