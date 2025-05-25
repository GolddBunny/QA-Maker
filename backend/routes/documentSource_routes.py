from flask import Blueprint, Response, jsonify, send_file, request
import os
import csv
import re
import urllib.parse
import subprocess
import tempfile
import shutil
import time
import io
import threading
import uuid
import atexit
import signal
import psutil
from firebase_config import bucket
source_bp = Blueprint('source', __name__)
from firebase_admin import firestore
from firebase_config import bucket
db = firestore.client()

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
CSV_PATH = os.path.join(BACKEND_DIR, 'context_data_sources.csv')

# LibreOffice 백그라운드 서비스 관리
class LibreOfficeService:
    def __init__(self):
        self.service_process = None
        self.service_port = None
        self.service_lock = threading.Lock()
        self.temp_dir = None
        
    def start_service(self):
        """LibreOffice를 백그라운드 서비스로 시작"""
        with self.service_lock:
            if self.service_process and self.service_process.poll() is None:
                print("LibreOffice 서비스가 이미 실행 중입니다.")
                return True
                
            try:
                # LibreOffice 경로 확인
                libreoffice_path = check_libreoffice_installation()
                if not libreoffice_path:
                    print("LibreOffice를 찾을 수 없습니다.")
                    return False
                
                # 사용 가능한 포트 찾기
                import socket
                sock = socket.socket()
                sock.bind(('', 0))
                self.service_port = sock.getsockname()[1]
                sock.close()
                
                # 임시 디렉토리 생성
                if self.temp_dir:
                    shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir = tempfile.mkdtemp(prefix="libreoffice_service_")
                
                # LibreOffice 서비스 시작
                cmd = [
                    libreoffice_path,
                    '--headless',
                    '--invisible',
                    '--nodefault',
                    '--nolockcheck',
                    '--nologo',
                    '--norestore',
                    f'--accept=socket,host=127.0.0.1,port={self.service_port};urp;'
                ]
                
                env = os.environ.copy()
                env['HOME'] = self.temp_dir
                env['TMPDIR'] = self.temp_dir
                
                print(f"LibreOffice 서비스 시작: 포트 {self.service_port}")
                self.service_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    cwd=self.temp_dir
                )
                
                # 서비스 시작 대기
                time.sleep(2)
                
                if self.service_process.poll() is None:
                    print(f"LibreOffice 서비스 시작 완료 (PID: {self.service_process.pid})")
                    return True
                else:
                    print("LibreOffice 서비스 시작 실패")
                    return False
                    
            except Exception as e:
                print(f"LibreOffice 서비스 시작 오류: {str(e)}")
                return False
    
    def stop_service(self):
        """LibreOffice 서비스 종료"""
        with self.service_lock:
            if self.service_process:
                try:
                    self.service_process.terminate()
                    self.service_process.wait(timeout=5)
                    print("LibreOffice 서비스 정상 종료")
                except:
                    try:
                        self.service_process.kill()
                        print("LibreOffice 서비스 강제 종료")
                    except:
                        pass
                self.service_process = None
            
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.temp_dir = None
    
    def is_running(self):
        """서비스 실행 상태 확인"""
        return self.service_process and self.service_process.poll() is None

# 전역 LibreOffice 서비스 인스턴스
libreoffice_service = LibreOfficeService()

# 애플리케이션 종료 시 서비스 정리
def cleanup_service():
    libreoffice_service.stop_service()

atexit.register(cleanup_service)

@source_bp.route('/api/context-sources', methods=['GET'])
def get_context_sources():
    """CSV 파일에서 추출한 headline 반환 - firestore의 original_filename 반환"""
    try:
        # 요청에서 page_id 파라미터 가져오기
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400
        
        headlines = set()  # 중복 제거
        
        if not os.path.exists(CSV_PATH):
            return jsonify({"error": f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}"}), 404
        
        print(f"CSV 파일 처리 중: {CSV_PATH}")
        
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row_num, row in enumerate(csv_reader, 1):
                #print(f"행 {row_num} 처리 중: {row}")
                
                # headline 처리
                if 'text' in row and row['text']:
                    # headline 추출 시도
                    headline = extract_headline(row['text'])
                    if headline:
                        #print(f"추출된 headline: '{headline}'")
                        headlines.add(headline)
                
                # headline 필드가 있는 경우
                elif 'headline' in row and row['headline'].strip():
                    headline = row['headline'].strip()
                    #print(f"직접 headline: '{headline}'")
                    headlines.add(headline)
        
        print(f"최종 headlines: {list(headlines)}")
        filename_mapping = {}
        try:
            docs = db.collection('document_files').where('page_id', '==', page_id).stream()
            for doc in docs:
                data = doc.to_dict()
                firebase_filename = data.get('firebase_filename')
                original_filename = data.get('original_filename')
                
                if firebase_filename and original_filename:
                    filename_mapping[firebase_filename] = original_filename
                    print(f"매핑 추가: {firebase_filename} -> {original_filename}")
        
        except Exception as e:
            print(f"Firestore 조회 오류: {e}")
        
        print(f"filename_mapping: {filename_mapping}")
        print(f"headlines: {list(headlines)}")
        
        # headlines 순서에 맞춰 original_filenames 배열 생성
        original_filenames = []
        for headline in headlines:
            # 확장자 붙여서 시도 (.pdf, .docx, .hwp 등)
            candidates = [
                headline + ".pdf",
                headline + ".docx",
                headline + ".hwp",
                headline + ".txt"
            ]
            
            # 매핑에 존재하는 파일명을 찾음
            original_name = next((filename_mapping[f] for f in candidates if f in filename_mapping), headline)
            
            original_filenames.append(original_name)
            print(f"headline: {headline} -> original: {original_name}")
        
        print(f"최종 original_filenames: {original_filenames}")
        
        return jsonify({
            "headlines": original_filenames
        })
    
    except Exception as e:
        print(f"CSV 처리 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

def extract_headline(text):
    """텍스트에서 headline 정보 추출"""
    if not text or not isinstance(text, str):
        return None
    
    try:
        #print(f"headline 추출 시도: '{text}'")
        
        # 방법 1: headline: 뒤에 오는 텍스트 추출 (영어/한글 모두 지원)
        # 더 포괄적인 정규식 사용
        headline_patterns = [
            r'headline:\s*([^|\n\r]+?)(?:\s*(?:page:|content:|headline:|\||$))',  # | 또는 다른 필드 전까지
            r'headline:\s*([^|\n\r]+)',  # 줄 끝까지
        ]
        
        for pattern in headline_patterns:
            headline_match = re.search(pattern, text, re.IGNORECASE)
            if headline_match and headline_match.group(1):
                headline = headline_match.group(1).strip()
                print(f"추출된 headline: '{headline}'")
                return headline
        
        print("headline 추출 실패")
        return None
        
    except Exception as e:
        print(f"headline 추출 중 오류: {str(e)}")
        return None

def check_libreoffice_installation():
    """LibreOffice 설치 여부 및 경로 확인"""
    possible_paths = [
        '/opt/homebrew/bin/soffice',  # Mac (Homebrew M1/M2)
        '/usr/local/bin/soffice',  # Mac (Homebrew Intel)
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',  # Mac (직접 설치)
        '/usr/bin/soffice',  # Linux
        '/usr/bin/libreoffice',  # Linux alternative
        'soffice',  # PATH에 있는 경우
        'libreoffice'  # PATH에 있는 경우
    ]
    
    for path in possible_paths:
        try:
            # which 명령어로도 확인
            if '/' not in path:
                result = subprocess.run(['which', path], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            else:
                if os.path.exists(path):
                    return path
        except:
            continue
    
    return None

# 빠른 변환을 위한 캐시
conversion_cache = {}
cache_lock = threading.Lock()

def is_hwp_file(file_path):
    """파일이 HWP 형식인지 확인"""
    return file_path.lower().endswith('.hwp')

def convert_to_pdf_fast(input_file):
    """빠른 PDF 변환 (서비스 모드 + 캐시)"""
    # HWP 파일은 변환하지 않음
    if is_hwp_file(input_file):
        print(f"HWP 파일은 PDF 변환을 지원하지 않습니다: {input_file}")
        return None
    
    # 파일 수정 시간 기반 캐시 키
    try:
        file_stat = os.stat(input_file)
        cache_key = f"{input_file}_{file_stat.st_mtime}_{file_stat.st_size}"
        
        # 캐시 확인
        with cache_lock:
            if cache_key in conversion_cache:
                print(f"캐시에서 PDF 반환: {input_file}")
                cached_data = conversion_cache[cache_key]
                pdf_stream = io.BytesIO(cached_data)
                pdf_stream.seek(0)
                return pdf_stream
        
        print(f"PDF 변환 시작: {input_file}")
        
        # LibreOffice 서비스 확인 및 시작
        if not libreoffice_service.is_running():
            print("LibreOffice 서비스 시작 중...")
            if not libreoffice_service.start_service():
                print("LibreOffice 서비스 시작 실패")
                return None
        
        # 임시 디렉토리에서 빠른 변환
        with tempfile.TemporaryDirectory(prefix="fast_convert_") as temp_dir:
            libreoffice_path = check_libreoffice_installation()
            if not libreoffice_path:
                print("LibreOffice 실행 파일을 찾을 수 없습니다")
                return None
                
            cmd = [
                libreoffice_path,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', temp_dir,
                input_file
            ]
            
            start_time = time.time()
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,  # 20초 타임아웃
                cwd=temp_dir
            )
            
            conversion_time = time.time() - start_time
            print(f"변환 시간: {conversion_time:.2f}초")
            
            if process.returncode != 0:
                print(f"PDF 변환 실패: {process.stderr}")
                return None
            
            # PDF 파일 찾기
            input_filename = os.path.basename(input_file)
            base_name = os.path.splitext(input_filename)[0]
            temp_pdf_file = os.path.join(temp_dir, f"{base_name}.pdf")
            
            # 짧은 대기 시간
            max_wait = 3
            wait_time = 0
            while not os.path.exists(temp_pdf_file) and wait_time < max_wait:
                time.sleep(0.1)
                wait_time += 0.1
            
            if not os.path.exists(temp_pdf_file):
                print("PDF 파일 생성 실패")
                return None
            
            # PDF 데이터 읽기 및 캐시 저장
            with open(temp_pdf_file, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
                
                # 캐시에 저장 (파일 크기 제한)
                if len(pdf_data) < 50 * 1024 * 1024:  # 50MB 미만만 캐시
                    with cache_lock:
                        # 캐시 크기 제한 (최대 10개 파일)
                        if len(conversion_cache) >= 10:
                            # 가장 오래된 항목 제거
                            oldest_key = next(iter(conversion_cache))
                            del conversion_cache[oldest_key]
                        
                        conversion_cache[cache_key] = pdf_data
                        #print(f"PDF 캐시에 저장: {len(pdf_data)} bytes")
                
                pdf_stream = io.BytesIO(pdf_data)
                pdf_stream.seek(0)
                return pdf_stream
    
    except Exception as e:
        print(f"PDF 변환 오류: {str(e)}")
        return None

@source_bp.route('/api/document/<path:filename>')
def get_document(filename):
    """문서 파일 제공 (PDF 뷰어용, HWP 제외)"""
    try:
        # 요청에서 page_id 파라미터 가져오기
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400
        
        decoded_filename = urllib.parse.unquote(filename)
        #print(f"요청된 파일명: '{decoded_filename}'")
        
        # Firestore에서 firebase_filename 조회
        docs = db.collection('document_files') \
                 .where('page_id', '==', page_id) \
                 .where('original_filename', '==', decoded_filename) \
                 .stream()

        firebase_filename = None
        for doc in docs:
            firebase_filename = doc.to_dict().get('firebase_filename')
            break

        if not firebase_filename:
            return jsonify({"error": "Firebase에 등록된 파일명을 찾을 수 없습니다."}), 404

        # 확장자 확인 (hwp면 제외)
        if firebase_filename.lower().endswith('.hwp'):
            return jsonify({
                "error": f"HWP 파일은 뷰어에서 지원하지 않습니다. 다운로드하여 확인해주세요: {decoded_filename}"
            }), 400

        # Firebase Storage 경로 구성
        blob_path = f"pages/{page_id}/documents/{firebase_filename}"
        blob = bucket.blob(blob_path)

        if not blob.exists():
            return jsonify({"error": f"Storage에 파일이 존재하지 않습니다: {firebase_filename}"}), 404

        # 임시 파일로 다운로드
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_path = temp_file.name

        print(f"[임시 다운로드 완료] {temp_path}")

        ext = os.path.splitext(firebase_filename)[1].lower()

        if ext == '.pdf':
            return send_file(temp_path, mimetype='application/pdf')
        
        # PDF 변환
        start = time.time()
        pdf_stream = convert_to_pdf_fast(temp_path)
        os.remove(temp_path)

        if not pdf_stream:
            return jsonify({"error": "문서 변환에 실패했습니다."}), 500

        print(f"[PDF 변환 완료] 소요 시간: {time.time() - start:.2f}s")

        return send_file(
            pdf_stream,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f"{decoded_filename}.pdf"
        )
    
    except Exception as e:
        print(f"문서 제공 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

@source_bp.route('/api/download/<path:filename>')
def download_document(filename):
    """원본 문서 파일 다운로드 (DOCX, HWP, PDF)"""
    try:
        # 요청에서 page_id 파라미터 가져오기
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400
        
        decoded_filename = urllib.parse.unquote(filename)
        #print(f"다운로드 요청된 파일명: '{decoded_filename}'")
        
        # Firestore에서 firebase_filename 조회
        doc_ref = db.collection('document_files').where('page_id', '==', page_id).where('original_filename', '==', decoded_filename)
        docs = doc_ref.stream()
        firebase_filename = None
        original_ext = None

        for doc in docs:
            data = doc.to_dict()
            firebase_filename = data.get('firebase_filename')
            original_ext = os.path.splitext(decoded_filename)[1] or os.path.splitext(firebase_filename)[1]
            break

        if not firebase_filename:
            return jsonify({"error": f"'{decoded_filename}'에 해당하는 파일을 찾을 수 없습니다"}), 404

        firebase_path = f"pages/{page_id}/documents/{firebase_filename}"
        blob = bucket.blob(firebase_path)

        if not blob.exists():
            return jsonify({"error": f"Firebase Storage에 파일이 존재하지 않습니다: {firebase_path}"}), 404

        file_data = blob.download_as_bytes()

        # MIME 타입 설정
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.hwp': 'application/x-hwp'
        }
        mime_type = mime_types.get(original_ext.lower(), 'application/octet-stream')

        return Response(
            file_data,
            mimetype=mime_type,
            headers={
                'Content-Disposition': f"attachment; filename*=UTF-8''{urllib.parse.quote(decoded_filename)}"
            }
        )
    
    except Exception as e:
        print(f"파일 다운로드 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 기존 PDF API 엔드포인트 (호환성 유지)
@source_bp.route('/api/pdf/<path:filename>')
def get_pdf(filename):
    """PDF 파일 제공 (호환성을 위한 별칭)"""
    return get_document(filename)