import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import firebase_admin
from firebase_admin import credentials, firestore, storage

# -------------------------
# Firebase 초기화
# -------------------------
current_dir = Path(__file__).parent
cred_path = current_dir / '../services/firebase/qamaker-e32d7-firebase-adminsdk-fbsvc-9c8756c5bc.json'

if not firebase_admin._apps:
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'qamaker-e32d7.firebasestorage.app'
    })

db = firestore.client()
bucket = storage.bucket()

# -------------------------
# URL 마이그레이션 함수
# -------------------------
def migrate_urls_to_firestore(page_id, max_workers=10):
    prefix = f"pages/{page_id}/urls/"
    blobs = list(bucket.list_blobs(prefix=prefix))
    print(f"총 {len(blobs)}개의 Storage blob 발견 (page_id={page_id})")

    # Storage 메타데이터 병렬 읽기
    def read_blob_metadata(blob):
        blob.reload()
        metadata = blob.metadata or {}
        url = metadata.get("url")
        date = metadata.get("date", blob.time_created.strftime("%Y-%m-%d"))
        if url:
            return {"url": url, "date": date}
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(read_blob_metadata, blobs))

    urls_data = [r for r in results if r is not None]
    print(f"{len(urls_data)}개의 URL 추출 완료")

    # Firestore 배치 쓰기 (page_id 서브컬렉션)
    batch = db.batch()
    batch_count = 0
    for i, url_entry in enumerate(urls_data):
        doc_ref = db.collection("url_list").document(page_id).collection("list").document()
        batch.set(doc_ref, url_entry)
        batch_count += 1

        if batch_count == 500:
            batch.commit()
            batch = db.batch()
            batch_count = 0

    if batch_count > 0:
        batch.commit()

    print(f"총 {len(urls_data)}개의 URL Firestore에 저장 완료 (page_id={page_id})")
    return len(urls_data)

# -------------------------
# main 실행
# -------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python migrate_urls.py <page_id>")
        sys.exit(1)

    page_id = sys.argv[1]
    print(f"page_id = {page_id} URL 마이그레이션 시작...")
    migrate_urls_to_firestore(page_id)
    print("마이그레이션 완료")