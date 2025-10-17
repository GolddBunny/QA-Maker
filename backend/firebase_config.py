import firebase_admin
from firebase_admin import credentials, storage, firestore
import os
from pathlib import Path

# 서비스 계정 키 JSON 파일 경로 (절대 경로로 수정)
current_dir = Path(__file__).parent
cred_path = current_dir / 'services' / 'firebase' / 'qamaker-e32d7-firebase-adminsdk-fbsvc-9c8756c5bc.json'

# Firebase 앱 초기화 (한 번만)
if not firebase_admin._apps:
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'qamaker-e32d7.firebasestorage.app'
    })

# Storage 버킷 객체
bucket = storage.bucket()

# Firestore 데이터베이스 객체
db = firestore.client()