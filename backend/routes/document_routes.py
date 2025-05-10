import os
import subprocess
import time
from flask import Blueprint, jsonify, request
from services.document_service.convert2txt import convert2txt

document_bp = Blueprint('document', __name__)

@document_bp.route('/has-output/<page_id>', methods=['GET'])
def has_output_folder(page_id):
    """output 폴더 존재 여부 확인"""
    base_path = f'../data/input/{page_id}'
    output_path = os.path.join(base_path, 'output')
    
    has_output = os.path.exists(output_path) and len(os.listdir(output_path)) > 0

    return jsonify({
        'success': True,
        'has_output': has_output
    })

@document_bp.route('/upload-documents/<page_id>', methods=['POST'])
def upload_documents(page_id):
    """document 업로드"""
    base_path, input_path, upload_path = ensure_page_directory(page_id)

    if 'files' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []

    for file in files:
        if file.filename == '':
            continue
        
        if file:
            original_filename = file.filename.strip()
            sanitized_filename = original_filename.replace(' ', '_')
            file_path = os.path.join(upload_path, os.path.basename(sanitized_filename))
            file.save(file_path)
            uploaded_files.append(file_path)
            print(f"파일 업로드 완료: {file_path}")

    return jsonify({
        'success': True, 
        'uploaded_files': uploaded_files
    })


@document_bp.route('/process-documents/<page_id>', methods=['POST'])
def process_documents(page_id):
    """document 처리"""
    try:
        base_path, input_path, upload_path = ensure_page_directory(page_id)

        convert2txt(upload_path, input_path)    # 문서 -> txt 변경
        print("모든 파일 .txt로 변환 완료")

        return jsonify({
            'success': True,
            'message': '문서 변환 완료'
        })

    except Exception as e:
        print("Flask 서버 오류:", str(e))
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500


@document_bp.route('/apply/<page_id>', methods=['POST'])
def apply_documents(page_id):
    """GraphRAG 인덱싱 처리"""
    try:
        base_path, input_path, upload_path = ensure_page_directory(page_id)

        # graphrag index 명령어 실행
        start_time = time.time()
        process = subprocess.run(['graphrag', 'index', '--root', base_path])
        end_time = time.time()
        execution_time = end_time - start_time
        print(execution_time)

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


@document_bp.route('/update/<page_id>', methods=['POST'])
def update(page_id):
    """document 업데이트"""
    try:
        base_path, input_path, upload_path = ensure_page_directory(page_id)

        convert2txt(upload_path, input_path)
        print("모든 파일 .txt로 변환 완료")

        start_time = time.time()
        subprocess.run(['graphrag', 'update', '--root', base_path])
        end_time = time.time()
        execution_time = end_time - start_time
        print(f'execution_time: {execution_time}')
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