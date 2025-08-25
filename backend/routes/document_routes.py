from datetime import datetime
import os
import subprocess
import tempfile
import time
from flask import Blueprint, jsonify, request
from services.document_service.hwp_to_md_txt import convert_hwp_file
from services.document_service.pdf_to_md_txt import convert_pdf_file
from services.document_service.convert2txt import convert2txt, convert_docx
from firebase_config import bucket
from werkzeug.utils import secure_filename
import uuid
from firebase_admin import firestore
import time

document_bp = Blueprint('document', __name__)

# Firestore 클라이언트
db = firestore.client()

@document_bp.route('/has-output/<page_id>', methods=['GET'])
def has_output_folder(page_id):
    """Firebase Storage의 output 폴더 존재 여부 확인"""
    prefix = f'pages/{page_id}/results/'
    blobs = list(bucket.list_blobs(prefix=prefix))

    has_output = len(blobs) > 0

    return jsonify({
        'success': True,
        'has_output': has_output
    })

# 문서 업로드 api
@document_bp.route('/upload-documents/<page_id>', methods=['POST'])
def upload_documents(page_id):
    """Firebase Storage에 문서 업로드"""
    
    if 'files' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    for file in files:
        if file.filename == '':
            continue

        # 파일 크기 계산 (업로드 전)
        file.seek(0, 2)  # 파일 끝으로 이동
        file_size_bytes = file.tell()
        file.seek(0)  # 파일 시작으로 되돌리기
        size_mb = file_size_bytes / (1024 * 1024)

        original_filename = file.filename
        ext = os.path.splitext(original_filename)[1]
        uuid_name = f"{uuid.uuid4().hex}{ext}"
        upload_path = f"pages/{page_id}/documents/{uuid_name}"

        # 날짜 포맷 지정
        today_str = datetime.now().strftime('%Y-%m-%d')

        # 1. Firebase blob 생성
        blob = bucket.blob(upload_path)

        # 2. metadata에 원본 파일명, 카테고리, 날짜 저장
        blob.metadata = {
            "original_filename": original_filename,
            "category": "unknown",
            "date": today_str
        }

        # 3. 파일 업로드
        blob.upload_from_file(file.stream, content_type=file.content_type)
        blob.make_public()

        document_data = {
            'original_filename': original_filename,
            'firebase_filename': uuid_name,
            'download_url': blob.public_url,
            'page_id': page_id,
            'upload_date': today_str,
            'category': "unknown",   
            'date': today_str,
            'size_mb': round(size_mb, 2)  # 크기 정보 추가  
        }

        # 문서명을 문서 ID로 사용하면 중복 이슈 있음 → UUID 또는 자동 ID 사용 권장
        db.collection('document_files').add(document_data)

        # 5. 클라이언트 응답용 리스트에도 추가
        uploaded_files.append(document_data)

        print(f"Uploaded 문서 to Firebase: {blob.public_url} (원본 이름: {original_filename})")

    return jsonify({
        'success': True,
        'uploaded_files': uploaded_files
    })

# adminPage에서 문서 목록 보기
@document_bp.route('/documents/<page_id>', methods=['GET'])
def get_uploaded_documents(page_id):
    try:
        docs_ref = db.collection('document_files').where('page_id', '==', page_id)
        docs = docs_ref.stream()

        result = []
        for doc in docs:
            data = doc.to_dict()
            # Firebase Storage에서 실제 파일 크기 가져오기
            firebase_filename = data.get('firebase_filename')
            size_mb = 0
            
            if firebase_filename:
                try:
                    blob_path = f"pages/{page_id}/documents/{firebase_filename}"
                    blob = bucket.blob(blob_path)
                    
                    # blob이 존재하면 크기 정보 가져오기
                    if blob.exists():
                        blob.reload()  # 메타데이터 새로고침
                        size_bytes = blob.size
                        size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
                except Exception as e:
                    print(f"파일 크기 조회 오류 ({firebase_filename}): {str(e)}")
                    size_mb = 0
                    
            result.append({
                'original_filename': data.get('original_filename'),
                'category': data.get('category', 'unknown'),
                'date': data.get('upload_date')
            })

        return jsonify({
            'success': True,
            'uploaded_files': result,
            'total_count': len(result)
        })
    except Exception as e:
        print("Firebase 오류:", str(e))
        return jsonify({'success': False, 'error': str(e)}), 500
    

# 문서 업로드 시 텍스트 추출
@document_bp.route('/process-documents/<page_id>', methods=['POST'])
def process_documents(page_id):
    """document 처리"""
    try:
        base_path, input_path, _ = ensure_page_directory(page_id)
        firebase_path = f"pages/{page_id}/documents"

        # Firestore에서 filename 매핑 가져오기
        filename_mapping = {}  # {firebase_filename: original_filename}
        docs = db.collection('document_files').where('page_id', '==', page_id).stream()
        for doc in docs:
            data = doc.to_dict()
            fb = data.get('firebase_filename')
            orig = data.get('original_filename')
            if fb and orig:
                filename_mapping[fb] = orig
                
        start_time = time.time()
        convert2txt(firebase_path, input_path, bucket, filename_mapping)
        end_time = time.time()
        execution_time = round(end_time - start_time)

        print("모든 파일 .txt로 변환 완료")
        return jsonify({
            'success': True,
            'message': '문서 변환 완료',
            'execution_time': execution_time
        })
    
    except Exception as e:
        end_time = time.time()
        execution_time = round(end_time - start_time) if 'start_time' in locals() else None
        print("Flask 서버 오류:", str(e))

        return jsonify({
            'success': False,
            'error': str(e),
            'execution_time': execution_time
        }), 500

    
# 문서 직접 업로드 시 텍스트 추출
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
                convert_pdf_file(file_path, output_path)
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
    input_path = os.path.join(base_path, 'input')  # 처리된 문서 텍스트 파일들을 저장할 폴더
    upload_path = f'../frontend/public/data/{page_id}/input' # 클라이언트에 노출할 폴더
    
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(input_path, exist_ok=True)
    os.makedirs(upload_path, exist_ok=True)
    
    return base_path, input_path, upload_path 

@document_bp.route('/download-crawled-documents/<page_id>', methods=['POST'])
def download_crawled_documents(page_id):
    """크롤링된 문서 URL 목록을 다운로드하여 Firebase에 저장"""
    try:
        data = request.get_json()
        if not data or 'doc_urls' not in data:
            return jsonify({
                'success': True,
                'message': '크롤링된 문서 URL이 없습니다. 다음 단계로 진행합니다.',
                'stats': {
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'skipped': 0,
                    'filtered_out': 0,
                    'firebase_uploaded': 0,
                    'firebase_failed': 0,
                    'local_deleted': 0
                }
            })
        
        doc_urls = data['doc_urls']
        if not isinstance(doc_urls, list) or not doc_urls:
            return jsonify({
                'success': True,
                'message': '다운로드할 문서 URL이 없습니다. 다음 단계로 진행하세요.',
                'stats': {
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'skipped': 0,
                    'filtered_out': 0,
                    'firebase_uploaded': 0,
                    'firebase_failed': 0,
                    'local_deleted': 0
                }
            })
        
        # DocumentDownloader 임포트
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'services', 'crawling_service'))
        from document_downloader import DocumentDownloader
        
        # 임시 다운로드 폴더 생성
        temp_download_folder = f'../data/temp_download/{page_id}'
        os.makedirs(temp_download_folder, exist_ok=True)
        
        # DocumentDownloader 인스턴스 생성
        downloader = DocumentDownloader(
            input_folder=temp_download_folder,
            domain="crawled",
            delay=1.0,
            upload_to_firebase=True,
            delete_local_after_upload=True,
            page_id=page_id
        )
        
        # 크롤링된 문서 URL 다운로드
        downloader.download_from_crawled_urls(doc_urls)
        
        # 통계 정보 반환
        stats = downloader.stats
        
        return jsonify({
            'success': True,
            'message': '크롤링된 문서 다운로드 완료',
            'stats': {
                'total': stats['total'],
                'success': stats['success'],
                'failed': stats['failed'],
                'skipped': stats['skipped'],
                'filtered_out': stats['filtered_out'],
                'firebase_uploaded': stats['firebase_uploaded'],
                'firebase_failed': stats['firebase_failed'],
                'local_deleted': stats['local_deleted']
            }
        })
        
    except Exception as e:
        print(f"크롤링된 문서 다운로드 오류: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500 