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
import unicodedata
import atexit
import signal
import psutil
import fitz
from firebase_config import bucket
from firebase_admin import firestore
source_bp = Blueprint('source', __name__)
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
    """CSV 파일에서 추출한 파일명 반환 - firestore의 original_filename 반환"""
    try:
        # 요청에서 page_id 파라미터 가져오기
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400
        
        filenames = set()  # 중복 제거
        
        if not os.path.exists(CSV_PATH):
            return jsonify({"error": f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}"}), 404
        
        print(f"CSV 파일 처리 중: {CSV_PATH}")
        
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row_num, row in enumerate(csv_reader, 1):
                print(f"행 {row_num} 처리 중")
                
                # text 필드에서 파일명 추출
                if 'text' in row and row['text']:
                    filename = extract_headline(row['text'])
                    if filename:
                        filenames.add(filename)
                
                # headline 필드가 별도로 있는 경우도 처리
                elif 'headline' in row and row['headline'].strip():
                    filename = row['headline'].strip()
                    print(f"직접 파일명: '{filename}'")
                    filenames.add(filename)
        
        print(f"추출된 파일명들: {list(filenames)}")
        
        # Firestore에서 filename mapping 가져오기
        filename_mapping = {}
        try:
            docs = db.collection('document_files').where('page_id', '==', page_id).stream()
            for doc in docs:
                data = doc.to_dict()
                firebase_filename = data.get('firebase_filename')
                original_filename = data.get('original_filename')
                
                if firebase_filename and original_filename:
                    # firebase_filename에서 확장자를 제거한 것을 키로 사용
                    base_firebase_name = os.path.splitext(firebase_filename)[0]
                    filename_mapping[base_firebase_name] = original_filename
                    print(f"매핑 추가: {base_firebase_name} -> {original_filename}")
        
        except Exception as e:
            print(f"Firestore 조회 오류: {e}")
        
        # 파일명에 대응하는 original_filename 찾기
        original_filenames = []
        for filename in filenames:
            # 정확히 일치하는 것을 먼저 찾기
            if filename in filename_mapping:
                original_filenames.append(filename_mapping[filename])
                print(f"정확한 매칭: {filename} -> {filename_mapping[filename]}")
                continue
            
            # 부분 일치 찾기 (CSV의 파일명이 원본 파일명에 포함되어 있는 경우)
            found = False
            for base_name, original_name in filename_mapping.items():
                if filename in base_name or base_name in filename:
                    original_filenames.append(original_name)
                    print(f"부분 매칭: {filename} -> {original_name}")
                    found = True
                    break
            
            # 매칭되는 것이 없으면 원래 파일명 사용
            if not found:
                original_filenames.append(filename)
                print(f"매칭 실패, 원본 사용: {filename}")
        
        print(f"최종 original_filenames: {original_filenames}")
        
        return jsonify({
            "headlines": original_filenames
        })
    
    except Exception as e:
        print(f"CSV 처리 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

def extract_headline(text):
    """텍스트에서 파일명 정보 추출"""
    if not text or not isinstance(text, str):
        return None
    
    try:
        # print(f"파일명 추출 시도: '{text[:100]}...'")
        
        headline_patterns = [
            # "**아래는 파일명 파일의 1페이지 내용입니다.**"
            r'\*\*아래는\s+(.+?)\s+파일의\s+\d+페이지\s+내용입니다\.\*\*',
            
            # "**아래는 파일명 파일의 페이지 내용입니다.**"
            r'\*\*아래는\s+(.+?)\s+파일의\s+.+?페이지\s+내용입니다\.\*\*',
            
            # 기존 headline: 패턴도 유지 (다른 데이터 형식 대응)
            r'headline:\s*([^|\n\r]+?)(?:\s*(?:page:|content:|headline:|\||$))',
            r'headline:\s*([^|\n\r]+)',
        ]
        
        for pattern in headline_patterns:
            headline_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if headline_match and headline_match.group(1):
                headline = headline_match.group(1).strip()
                print(f"추출된 파일명: '{headline}'")
                return headline
        
        print("파일명 추출 실패")
        return None
        
    except Exception as e:
        print(f"파일명 추출 중 오류: {str(e)}")
        return None

def get_highlight_content_for_file(filename):
    """특정 파일에 대한 하이라이트할 content 내용들을 CSV에서 가져오기"""
    if not os.path.exists(CSV_PATH):
        return []
    
    highlight_texts = []
    base_filename = os.path.splitext(filename)[0]
    
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                # 파일명이 매치되는 경우
                extracted_filename = None
                if 'text' in row and row['text']:
                    extracted_filename = extract_headline(row['text'])
                elif 'headline' in row and row['headline'].strip():
                    extracted_filename = row['headline'].strip()
                
                # 파일명이 일치하는지 확인 (부분 매칭도 허용)
                if extracted_filename and (
                    extracted_filename == base_filename or 
                    base_filename in extracted_filename or 
                    extracted_filename in base_filename
                ):
                    # content 추출
                    content = None
                    if 'text' in row and row['text']:
                        content = extract_content(row['text'])
                    elif 'content' in row and row['content'].strip():
                        content = row['content'].strip()
                    
                    if content:
                        # 하이라이트할 텍스트를 문장 단위로 분할
                        sentences = content.split('.')
                        for sentence in sentences:
                            sentence = sentence.strip()
                            if len(sentence) >= 20:  # 너무 짧은 문장은 제외
                                highlight_texts.append(sentence)
                                print(f"하이라이트 텍스트 추가: {sentence[:30]}...")
    
    except Exception as e:
        print(f"하이라이트 텍스트 추출 오류: {str(e)}")
    
    return highlight_texts

def extract_content(text):
    """텍스트에서 content 정보 추출 - 실제 문서 내용 부분"""
    if not text or not isinstance(text, str):
        return None
    
    try:
        # 실제 데이터에서 내용 추출 패턴들
        content_patterns = [
            # "**아래는 ... 페이지 내용입니다.**" 다음에 오는 실제 내용
            r'\*\*아래는\s+.+?파일의\s+.+?페이지\s+내용입니다\.\*\*\s*(.*?)(?=\*\*아래는|\Z)',
            
            # 기존 content: 패턴도 유지
            r'content:\s*([^|\n\r]+?)(?:\s*(?:page:|content:|headline:|\||$))',
            r'content:\s*([^|\n\r]+)',
        ]
        
        for pattern in content_patterns:
            content_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if content_match and content_match.group(1):
                content = content_match.group(1).strip()
                # 너무 짧은 내용은 제외 (최소 10자 이상)
                if len(content) >= 10:
                    print(f"추출된 내용: '{content[:50]}...'")
                    return content
        
        return None
        
    except Exception as e:
        print(f"내용 추출 중 오류: {str(e)}")
        return None

def add_highlights_to_pdf(pdf_stream, highlight_texts):
    """PDF에 하이라이트 추가"""
    if not highlight_texts:
        return pdf_stream
    
    try:
        # PDF 문서 열기
        pdf_document = fitz.open(stream=pdf_stream.getvalue(), filetype="pdf")
        
        # 각 페이지에서 텍스트 검색하고 하이라이트 추가
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            for highlight_text in highlight_texts:
                # 텍스트를 단어별로 분리해서 검색
                words = highlight_text.split()
                
                # 전체 텍스트로 먼저 검색
                text_instances = page.search_for(highlight_text)
                if text_instances:
                    for inst in text_instances:
                        highlight = page.add_highlight_annot(inst)
                        highlight.set_colors(stroke=[1, 1, 0])  # 노란색
                        highlight.update()
                    # print(f"전체 텍스트 하이라이트 추가: '{highlight_text}' (페이지 {page_num + 1})")
                    continue
                
                # 전체 텍스트가 안되면 부분 텍스트로 검색
                found_any = False
                for word in words:
                    if len(word.strip()) < 5:  # 너무 짧은 단어는 제외
                        continue
                        
                    word_instances = page.search_for(word.strip())
                    if word_instances:
                        for inst in word_instances:
                            highlight = page.add_highlight_annot(inst)
                            highlight.set_colors(stroke=[1, 1, 0])  # 노란색
                            highlight.update()
                        found_any = True
                
                if found_any:
                    # print(f"부분 텍스트 하이라이트 추가: '{highlight_text}' (페이지 {page_num + 1})")
                    print(f"부분 텍스트 하이라이트 추가: 페이지 {page_num + 1}")

        # 수정된 PDF를 새로운 스트림으로 저장
        output_stream = io.BytesIO()
        pdf_document.save(output_stream)
        pdf_document.close()
        
        output_stream.seek(0)
        return output_stream
    
    except Exception as e:
        print(f"PDF 하이라이트 추가 오류: {str(e)}")
        return pdf_stream

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
    """문서 파일 제공 (Firebase 연동 + PDF 뷰어용, HWP 제외) - 하이라이팅 기능 추가"""
    try:
        # page_id 쿼리 파라미터 필수
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400

        # 파일 이름 URL 디코딩 + 확장자 제거
        decoded_filename = urllib.parse.unquote(filename)
        base_filename = os.path.splitext(decoded_filename)[0]

        print(f"[요청] filename: '{decoded_filename}', page_id: '{page_id}'")

        # Firestore에서 해당 page_id의 문서들 가져오기
        docs = db.collection('document_files') \
                .where('page_id', '==', page_id) \
                .stream()

        matched_doc = next(
            (doc for doc in docs
            if unicodedata.normalize('NFC', os.path.splitext(doc.to_dict().get('original_filename', ''))[0])
                == unicodedata.normalize('NFC', base_filename)),
            None
        )

        if not matched_doc:
            return jsonify({
                "error": f"Firestore에서 page_id={page_id}, filename='{decoded_filename}'에 해당하는 문서를 찾을 수 없습니다."
            }), 404

        firebase_filename = matched_doc.to_dict().get('firebase_filename')
        if not firebase_filename:
            return jsonify({"error": "Firebase 파일명이 누락되었습니다."}), 404

        print(f"[파이어스토어 조회 완료] firebase_filename: '{firebase_filename}'")

        # HWP 파일 예외 처리
        if firebase_filename.lower().endswith('.hwp'):
            return jsonify({
                "error": f"HWP 파일은 뷰어에서 지원하지 않습니다. 다운로드하여 확인해주세요: {decoded_filename}"
            }), 400

        # Firebase Storage 경로 지정
        blob_path = f"pages/{page_id}/documents/{firebase_filename}"
        blob = bucket.blob(blob_path)

        if not blob.exists():
            print(f"[경고] Storage에 존재하지 않는 경로: {blob_path}")
            return jsonify({"error": f"Storage에 파일이 존재하지 않습니다: {firebase_filename}"}), 404

        # 파일을 임시 디렉토리에 다운로드
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_path = temp_file.name

        print(f"[파일 다운로드 성공] 경로: {temp_path}")

        ext = os.path.splitext(firebase_filename)[1].lower()

        # PDF면 바로 스트림으로 변환
        if ext == '.pdf':
            with open(temp_path, 'rb') as f:
                pdf_stream = io.BytesIO(f.read())
        else:
            # PDF로 변환 시도
            start = time.time()
            pdf_stream = convert_to_pdf_fast(temp_path)
            
            if not pdf_stream:
                os.remove(temp_path)
                return jsonify({"error": "문서 변환에 실패했습니다."}), 500
            
            print(f"[PDF 변환 완료] 소요 시간: {time.time() - start:.2f}s")

        os.remove(temp_path)  # 원본 파일 삭제

        # CSV에서 하이라이트할 텍스트 추출
        highlight_texts = get_highlight_content_for_file(base_filename)
        
        # 하이라이트 추가
        if highlight_texts:
            print(f"[하이라이트 추가] {len(highlight_texts)}개의 텍스트")
            pdf_stream = add_highlights_to_pdf(pdf_stream, highlight_texts)

        return send_file(
            pdf_stream,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f"{decoded_filename}.pdf"
        )

    except Exception as e:
        print(f"[오류 발생] {str(e)}")
        return jsonify({"error": str(e)}), 500


@source_bp.route('/api/download/<path:filename>')
def download_document(filename):
    """원본 문서 파일 다운로드 (DOCX, HWP, PDF)"""
    try:
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400
        
        decoded_filename = urllib.parse.unquote(filename)
        requested_name_no_ext, requested_ext = os.path.splitext(decoded_filename)

        docs = db.collection('document_files').where('page_id', '==', page_id).stream()

        matched_doc = None
        for doc in docs:
            data = doc.to_dict()
            original_fn = data.get('original_filename', '')

            original_name_no_ext, original_ext = os.path.splitext(original_fn)

            # 한글 정규화해서 비교 (확장자 없이 비교)
            if requested_ext:
                # 요청 파일명에 확장자가 있으면 전체 비교
                if unicodedata.normalize('NFC', original_fn) == unicodedata.normalize('NFC', decoded_filename):
                    matched_doc = data
                    break
            else:
                # 요청 파일명에 확장자가 없으면 Firestore 파일명 확장자 제거 후 비교
                if unicodedata.normalize('NFC', original_name_no_ext) == unicodedata.normalize('NFC', requested_name_no_ext):
                    matched_doc = data
                    break

        if not matched_doc:
            return jsonify({"error": f"'{decoded_filename}'에 해당하는 파일을 찾을 수 없습니다"}), 404

        firebase_filename = matched_doc.get('firebase_filename')
        if not firebase_filename:
            return jsonify({"error": "Firebase 파일명이 누락되었습니다."}), 404

        firebase_path = f"pages/{page_id}/documents/{firebase_filename}"
        blob = bucket.blob(firebase_path)

        if not blob.exists():
            return jsonify({"error": f"Firebase Storage에 파일이 존재하지 않습니다: {firebase_path}"}), 404

        file_data = blob.download_as_bytes()

        # 다운로드 시 확장자 기준은 Firestore 원본 파일명 사용
        _, original_ext = os.path.splitext(matched_doc.get('original_filename', ''))

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
                'Content-Disposition': f"attachment; filename*=UTF-8''{urllib.parse.quote(matched_doc.get('original_filename', decoded_filename))}"
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