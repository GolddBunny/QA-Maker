import firebase_admin
from firebase_admin import credentials, storage

# 서비스 계정 키 JSON 파일 경로
cred_path = './services/firebase/qamaker-e32d7-firebase-adminsdk-fbsvc-0408d84c8c.json'

# Firebase 앱 초기화 (한 번만)
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'qamaker-e32d7.firebasestorage.app'
    })

# Storage 버킷 객체
bucket = storage.bucket()