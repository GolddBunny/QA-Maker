import os
import subprocess
import time
from flask import Blueprint, jsonify, request
from services.document_service.convert2txt import convert2txt
from firebase_config import bucket

generate_bp = Blueprint('generate', __name__)

@generate_bp.route('/apply/<page_id>', methods=['POST'])
def apply_documents(page_id):
    """GraphRAG 인덱싱 처리"""
    try:
        base_path, input_path, upload_path = ensure_page_directory(page_id)
        output_path = os.path.join(base_path, 'output')

        # graphrag index 명령어 실행
        start_time = time.time()
        process = subprocess.run(['graphrag', 'index', '--root', base_path])
        end_time = time.time()
        execution_time = end_time - start_time
        print(execution_time)

        # output 폴더 내부 파일 Firebase로 업로드
        uploaded_files = []
        if os.path.exists(output_path):
            for filename in os.listdir(output_path):
                file_path = os.path.join(output_path, filename)

                if os.path.isfile(file_path):
                    # Firebase Storage에 업로드 경로
                    firebase_path = f'pages/{page_id}/results/{filename}'

                    blob = bucket.blob(firebase_path)
                    blob.upload_from_filename(file_path)
                    blob.make_public()

                    print(f"Uploaded {filename} → {firebase_path}")
                    uploaded_files.append(firebase_path)

                    # 업로드 후 파일 삭제
                    os.remove(file_path)
                    print(f"Deleted local file: {file_path}")

        return jsonify({
            'success': True,
            'execution_time': execution_time
        })

    except Exception as e:
        print("Flask 서버 오류:", str(e))
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@generate_bp.route('/update/<page_id>', methods=['POST'])
def update(page_id):
    """증분 인덱싱"""
    try:
        base_path, input_path, upload_path = ensure_page_directory(page_id)
        output_path = os.path.join(base_path, 'output')

        downloaded = download_output_files_from_firebase(page_id, output_path)
        if not downloaded:
            print("⚠ 기존 결과 파일이 Firebase에 존재하지 않습니다.")
        
        start_time = time.time()
        subprocess.run(['graphrag', 'update', '--root', base_path])
        end_time = time.time()
        execution_time = end_time - start_time
        print(f'execution_time: {execution_time}')
        
        # output 폴더 내부 파일 Firebase로 업로드
        uploaded_files = []
        if os.path.exists(output_path):
            for filename in os.listdir(output_path):
                file_path = os.path.join(output_path, filename)

                if os.path.isfile(file_path):
                    # Firebase Storage에 업로드 경로
                    firebase_path = f'pages/{page_id}/results/{filename}'

                    blob = bucket.blob(firebase_path)
                    blob.upload_from_filename(file_path)
                    blob.make_public()

                    print(f"Uploaded {filename} → {firebase_path}")
                    uploaded_files.append(firebase_path)

                    # 업로드 후 파일 삭제
                    os.remove(file_path)
                    print(f"Deleted local file: {file_path}")

        return jsonify({'success': True})
    
    except Exception as e:
        print("Flask update 오류: ", str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
# 공통 디렉토리 유틸리티 함수
def ensure_page_directory(page_id):
    """페이지 디렉토리 확인"""
    base_path = f'../data/input/{page_id}'
    input_path = os.path.join(base_path, 'input')
    upload_path = f'../frontend/public/data/{page_id}/input'
    
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(input_path, exist_ok=True)
    os.makedirs(upload_path, exist_ok=True)
    
    return base_path, input_path, upload_path 


def download_output_files_from_firebase(page_id, output_path):
    prefix = f'pages/{page_id}/results/'
    blobs = bucket.list_blobs(prefix=prefix)

    os.makedirs(output_path, exist_ok=True)
    
    found = False
    for blob in blobs:
        if blob.name.endswith("/"):  # 디렉토리인 경우 무시
            continue

        filename = os.path.basename(blob.name)
        local_path = os.path.join(output_path, filename)

        blob.download_to_filename(local_path)
        print(f"Downloaded {blob.name} → {local_path}")
        found = True
    
    return found