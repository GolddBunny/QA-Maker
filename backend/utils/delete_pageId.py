import firebase_admin
from firebase_admin import credentials, firestore, storage
from pathlib import Path

# 제외할 Page ID 목록
keep_page_ids = [
    "1748513655420", "1748538358464", "1750851417434", "1751437761028",
    "1751441568994", "1751455243604", "1751454392954", "1751517675883",
    "1751469826147", "1751548321186", "1751549097872", "1753520017701",
    "1753520431120", "1753533922120", "1753534911979", "1754472556761",
    "1754477460904", "1754544646817", "1754546649808", "1754554176373",
    "1754649732194", "1755047578460", "1755078792500", "1755081652797",
    "1755142860772", "1755166581835", "1755172386846", "1755322258086",
    "1755480639734"
]

# Firebase 초기화
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
# Storage에서 삭제
# -------------------------
def delete_storage_pages_except_keep():
    blobs = list(bucket.list_blobs(prefix="pages/"))
    for blob in blobs:
        # pages/<page_id>/... 형태에서 page_id 추출
        parts = blob.name.split('/')
        if len(parts) > 1:
            page_id = parts[1]
            if page_id not in keep_page_ids:
                print(f"Deleting Storage: {blob.name}")
                blob.delete()

# -------------------------
# Firestore에서 삭제
# -------------------------
def delete_firestore_pages_except_keep():
    # 1. dashboard 컬렉션
    docs = db.collection("dashboard").stream()
    for doc in docs:
        if doc.id not in keep_page_ids:
            print(f"Deleting Firestore dashboard: {doc.id}")
            doc.reference.delete()

    # 2. document_files 컬렉션 (필드에 page_id 존재하면 삭제)
    docs = db.collection("document_files").stream()
    for doc in docs:
        data = doc.to_dict()
        if "page_id" in data and data["page_id"] not in keep_page_ids:
            print(f"Deleting Firestore document_files: {doc.id}")
            doc.reference.delete()

    # 3. pages 컬렉션
    docs = db.collection("pages").stream()
    for doc in docs:
        if doc.id not in keep_page_ids:
            print(f"Deleting Firestore pages: {doc.id}")
            doc.reference.delete()

    # 4. urls 컬렉션 (서브컬렉션 또는 필드 확인)
    urls_col = db.collection("url_list")
    docs = urls_col.stream()
    for doc in docs:
        page_id = doc.id
        if page_id not in keep_page_ids:
            print(f"Deleting Firestore urls: {page_id}")
            # 서브컬렉션 삭제
            sub_docs = urls_col.document(page_id).collection("list").stream()
            for sub_doc in sub_docs:
                sub_doc.reference.delete()
            # 페이지 문서 삭제
            doc.reference.delete()

# -------------------------
# 실행
# -------------------------
if __name__ == "__main__":
    print("Storage 삭제 시작...")
    delete_storage_pages_except_keep()
    print("Firestore 삭제 시작...")
    delete_firestore_pages_except_keep()
    print("완료")