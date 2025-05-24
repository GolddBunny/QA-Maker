import os
import subprocess
import tempfile
import time
from flask import Blueprint, jsonify, request
from services.document_service.hwp2txt import convert_hwp_file
from services.document_service.pdf2txt import extract_text_and_tables
from services.document_service.convert2txt import convert2txt, convert_docx

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
        
        convert2txt(upload_path, input_path)  # 문서 -> txt 변경
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

@document_bp.route('/process-document-direct', methods=['POST'])
def process_document_direct():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'})

    file = request.files['file']
    filename = file.filename
    lower_name = filename.lower()

    try:
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, filename)
            file.save(file_path)

            text = ""

            if lower_name.endswith('.hwp'):
                output_path = os.path.join(temp_dir, "output.txt")
                convert_hwp_file(file_path, output_path)
                with open(output_path, 'r', encoding='utf-8') as f:
                    text = f.read()

            elif lower_name.endswith('.pdf'):
                output_path = os.path.join(temp_dir, "output.txt")
                extract_text_and_tables(file_path, output_path)
                with open(output_path, 'r', encoding='utf-8') as f:
                    text = f.read()

            elif lower_name.endswith('.docx'):
                output_path = os.path.join(temp_dir, "output.txt")
                convert_docx(file_path, output_path)
                with open(output_path, 'r', encoding='utf-8') as f:
                    text = f.read()

            elif lower_name.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                base_name = os.path.splitext(filename)[0]
                text = f"headline: {base_name}\ncontent:\n{raw_text}"

            else:
                return jsonify({'success': False, 'message': 'Unsupported file type'})

            return jsonify({'success': True, 'content': text})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    
    
@document_bp.route('/document/content/<page_id>', methods=['GET'])
def get_document_content(page_id):
    """처리된 문서 내용 가져오기"""
    try:
        base_path, input_path, _ = ensure_page_directory(page_id)
        
        # 처리된 문서 텍스트 파일들을 읽어 내용 반환
        document_content = ""
        
        for file_name in os.listdir(input_path):
            if file_name.endswith(".txt") and not "crawled_" in file_name:
                file_path = os.path.join(input_path, file_name)
                with open(file_path, 'r', encoding='utf-8') as file:
                    document_content += f"--- {file_name} ---\n"
                    document_content += file.read() + "\n\n"
        
        return document_content
    
    except Exception as e:
        return jsonify({"success": False, "error": f"문서 내용 가져오기 실패: {str(e)}"}), 500
    
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