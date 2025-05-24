import firebase_admin
from firebase_admin import credentials, storage

# 서비스 계정 키 JSON 파일 경로
cred_path = 'firebase/serviceAccountKey.json'

# Firebase 앱 초기화 (한 번만)
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'your-project-id.appspot.com'
    })

# Storage 버킷 객체
bucket = storage.bucket()