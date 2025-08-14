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
import fitz
from collections import defaultdict
import difflib
import unicodedata
import threading
import uuid
import unicodedata
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

# context-sources API에서 content 정보도 함께 반환하도록 수정

@source_bp.route('/api/context-sources', methods=['GET'])
def get_context_sources():
    """CSV 파일에서 추출한 headline과 content 반환 - firestore의 original_filename 반환"""
    try:
        # 요청에서 page_id 파라미터 가져오기
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400
        
        headlines_data = []  # headline과 content를 함께 저장
        
        if not os.path.exists(CSV_PATH):
            return jsonify({"error": f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}"}), 404
        
        print(f"CSV 파일 처리 중: {CSV_PATH}")
        
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row_num, row in enumerate(csv_reader, 1):
                
                headline = None
                content = ""
                
                # headline 처리
                if 'text' in row and row['text']:
                    # headline 추출 시도
                    headline = extract_headline(row['text'])
                    # content 추출 시도
                    content = extract_content(row['text'])
                
                # headline 필드가 있는 경우
                elif 'headline' in row and row['headline'].strip():
                    headline = row['headline'].strip()
                    content = row.get('content', '').strip()
                
                if headline:
                    headlines_data.append({
                        'headline': headline,
                        'content': content
                    })
        
        print(f"최종 headlines_data: {headlines_data}")
        
        # Firestore에서 파일명 매핑 정보 가져오기
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
        
        # headlines_data에 original_filename 매핑
        result_data = []
        for item in headlines_data:
            headline = item['headline']
            content = item['content']
            
            # 확장자 붙여서 시도 (.pdf, .docx, .hwp 등)
            candidates = [
                headline + ".pdf",
                headline + ".docx", 
                headline + ".hwp",
                headline + ".txt"
            ]
            
            # 매핑에 존재하는 파일명을 찾음
            original_name = next((filename_mapping[f] for f in candidates if f in filename_mapping), headline)
            
            result_data.append({
                'headline': original_name,
                'content': content
            })
            print(f"headline: {headline} -> original: {original_name}, content: {content[:50]}...")
        
        return jsonify({
            "headlines": [item['headline'] for item in result_data],
            "headlines_data": result_data  # headline과 content 정보 모두 포함
        })
    
    except Exception as e:
        print(f"CSV 처리 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

def extract_content(text):
    """텍스트에서 content 정보 추출"""
    if not text or not isinstance(text, str):
        return ""
    
    try:
        # content: 뒤에 오는 텍스트 추출
        content_patterns = [
            r'content:\s*([^|\n\r]+?)(?:\s*(?:page:|headline:|content:|\||$))',
            r'content:\s*([^|\n\r]+)',
        ]
        
        for pattern in content_patterns:
            content_match = re.search(pattern, text, re.IGNORECASE)
            if content_match and content_match.group(1):
                content = content_match.group(1).strip()
                print(f"추출된 content: '{content[:50]}...'")
                return content
        
        return ""
        
    except Exception as e:
        print(f"content 추출 중 오류: {str(e)}")
        return ""

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

# document API에 하이라이팅 기능 추가
@source_bp.route('/api/document/<path:filename>')
def get_document(filename):
    """문서 파일 제공 (Firebase 연동 + PDF 뷰어용 + 하이라이팅, HWP 제외)"""
    try:
        # page_id 쿼리 파라미터 필수
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400

        # 하이라이팅할 텍스트 파라미터 가져오기
        highlight_text = request.args.get('highlight', '').strip()
        
        # print(f"[요청 받음] filename: '{filename}', highlight: '{highlight_text}'")

        # 파일 이름 URL 디코딩 + 확장자 제거
        decoded_filename = urllib.parse.unquote(filename)
        base_filename = os.path.splitext(decoded_filename)[0]

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
                "error": f"문서를 찾을 수 없습니다: {decoded_filename}"
            }), 404

        firebase_filename = matched_doc.to_dict().get('firebase_filename')
        if not firebase_filename:
            return jsonify({"error": "Firebase 파일명이 누락되었습니다."}), 404

        # HWP 파일 예외 처리
        if firebase_filename.lower().endswith('.hwp'):
            return jsonify({
                "error": f"HWP 파일은 뷰어에서 지원하지 않습니다: {decoded_filename}"
            }), 400

        # Firebase Storage에서 파일 다운로드
        blob_path = f"pages/{page_id}/documents/{firebase_filename}"
        blob = bucket.blob(blob_path)

        if not blob.exists():
            return jsonify({"error": f"Storage에 파일이 존재하지 않습니다: {firebase_filename}"}), 404

        # 임시 파일에 다운로드
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(firebase_filename)[1]) as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_path = temp_file.name

        ext = os.path.splitext(firebase_filename)[1].lower()

        final_pdf_path = None

        # PDF인 경우
        if ext == '.pdf':
            if highlight_text:
                print(f"[PDF 하이라이팅] 원본 PDF에 하이라이팅 적용")
                final_pdf_path = add_pdf_highlighting(temp_path, highlight_text)
            else:
                final_pdf_path = temp_path
        else:
            # 다른 형식은 PDF로 변환
            print(f"[PDF 변환] {ext} 파일을 PDF로 변환 중")
            pdf_stream = convert_to_pdf_fast(temp_path)
            
            if not pdf_stream:
                os.remove(temp_path)
                return jsonify({"error": "문서 변환에 실패했습니다."}), 500

            # 변환된 PDF를 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                temp_pdf.write(pdf_stream.getvalue())
                converted_pdf_path = temp_pdf.name

            # 하이라이팅 적용
            if highlight_text:
                print(f"[변환 후 하이라이팅] 변환된 PDF에 하이라이팅 적용")
                final_pdf_path = add_pdf_highlighting(converted_pdf_path, highlight_text)
                # 변환된 PDF 파일 정리 (하이라이팅된 파일과 다른 경우)
                if final_pdf_path != converted_pdf_path:
                    os.remove(converted_pdf_path)
            else:
                final_pdf_path = converted_pdf_path

        # 원본 파일 정리
        if final_pdf_path != temp_path:
            os.remove(temp_path)

        # 최종 PDF 반환
        return send_file(
            final_pdf_path,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=f"{decoded_filename}.pdf"
        )

    except Exception as e:
        print(f"[전체 오류] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def extract_meaningful_words(text):
    """텍스트에서 의미있는 단어들을 추출"""
    # 마크다운 표 문법 제거 (|, -, : 등)
    text = re.sub(r'[|:\-\*\#\`\[\]]+', ' ', text)
    
    # 한글, 영문, 숫자만 추출 (2글자 이상)
    words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text)
    
    # 불용어 제거
    stop_words = {
        '그리고', '하지만', '그러나', '따라서', '또한', '그런데', '이것', '저것', '여기서',
        '입니다', '습니다', '한다', '있다', '없다', '되다', '하다', '이다', '아니다',
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'
    }
    
    # 의미있는 단어만 필터링
    meaningful_words = []
    for word in words:
        if len(word) >= 2 and word not in stop_words:
            # 너무 짧거나 단순한 패턴 제외
            if not re.match(r'^[0-9]+$', word) and len(word) >= 3:
                meaningful_words.append(word)
    
    return meaningful_words

def find_word_combinations_in_text(page_text, target_words, min_match_ratio=0.3):
    """페이지에서 단어 조합을 찾아 위치 반환"""
    if not target_words:
        return []
    
    # 페이지 텍스트를 문장 단위로 분할
    sentences = re.split(r'[.!?]\s*|\n\s*', page_text)
    matches = []
    
    for sentence in sentences:
        if len(sentence.strip()) < 10:  # 너무 짧은 문장 제외
            continue
            
        sentence_words = extract_meaningful_words(sentence)
        
        # 대상 단어들 중 몇 개가 이 문장에 있는지 확인
        found_words = []
        for target_word in target_words:
            for sentence_word in sentence_words:
                # 유사도 검사 (완전 일치 또는 높은 유사도)
                if (target_word.lower() == sentence_word.lower() or 
                    difflib.SequenceMatcher(None, target_word.lower(), sentence_word.lower()).ratio() > 0.8):
                    found_words.append(target_word)
                    break
        
        # 최소 매칭 비율 확인
        match_ratio = len(found_words) / len(target_words)
        if match_ratio >= min_match_ratio:
            matches.append({
                'sentence': sentence.strip(),
                'found_words': found_words,
                'match_ratio': match_ratio,
                'total_target_words': len(target_words)
            })
    
    # 매칭 비율이 높은 순으로 정렬
    matches.sort(key=lambda x: x['match_ratio'], reverse=True)
    return matches

def add_pdf_highlighting_word_based(pdf_path, highlight_text):
    """단어 조합 기반 PDF 하이라이팅"""
    try:
        print(f"[하이라이팅 시작] PDF: {pdf_path}")
        print(f"[원본 텍스트] {highlight_text[:100]}...")
        
        # PyMuPDF로 PDF 열기
        doc = fitz.open(pdf_path)
        
        # 대상 텍스트에서 의미있는 단어들 추출
        target_words = extract_meaningful_words(highlight_text)
        print(f"[추출된 핵심 단어] {target_words[:10]}")  # 처음 10개만 표시
        
        if not target_words:
            print("추출할 수 있는 의미있는 단어가 없습니다.")
            doc.close()
            return pdf_path
        
        highlighted = False
        total_highlights = 0
        
        # 모든 페이지 검색
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            
            # 1단계: 전체 텍스트 정확 매칭 시도 (기존 방식)
            clean_highlight_text = re.sub(r'[|:\-\*\#\`\[\]\s]+', ' ', highlight_text).strip()
            exact_matches = page.search_for(clean_highlight_text)
            
            if exact_matches:
                for match in exact_matches:
                    highlight = page.add_highlight_annot(match)
                    highlight.set_colors(stroke=[1, 0, 0], fill=[1, 0.8, 0.8])  # 빨간색 (완전일치)
                    highlight.set_opacity(0.6)
                    highlight.update()
                    highlighted = True
                    total_highlights += 1
                print(f"[완전 일치] 페이지 {page_num + 1}에서 {len(exact_matches)}개 발견")
                continue
            
            # 2단계: 단어 조합 매칭
            matches = find_word_combinations_in_text(page_text, target_words, min_match_ratio=0.3)
            
            if matches:
                print(f"[페이지 {page_num + 1}] {len(matches)}개의 후보 문장 발견")
                
                for i, match in enumerate(matches[:3]):  # 상위 3개만 처리
                    sentence = match['sentence']
                    match_ratio = match['match_ratio']
                    
                    print(f"  - 매칭률 {match_ratio:.1%}: {sentence[:50]}...")
                    
                    # 문장을 PDF에서 찾아 하이라이트
                    sentence_clean = re.sub(r'\s+', ' ', sentence).strip()
                    sentence_instances = page.search_for(sentence_clean)
                    
                    if sentence_instances:
                        color_intensity = match_ratio  # 매칭률에 따라 색상 강도 조절
                        for inst in sentence_instances:
                            highlight = page.add_highlight_annot(inst)
                            if match_ratio >= 0.7:
                                # 높은 매칭률 - 노란색
                                highlight.set_colors(stroke=[1, 1, 0], fill=[1, 1, 0])
                            elif match_ratio >= 0.5:
                                # 중간 매칭률 - 초록색
                                highlight.set_colors(stroke=[0, 1, 0], fill=[0.8, 1, 0.8])
                            else:
                                # 낮은 매칭률 - 파란색
                                highlight.set_colors(stroke=[0, 0, 1], fill=[0.8, 0.8, 1])
                            
                            highlight.set_opacity(0.4 + color_intensity * 0.3)
                            highlight.update()
                            highlighted = True
                            total_highlights += 1
                    else:
                        # 문장을 찾지 못했다면 개별 단어들을 하이라이트
                        found_words = match['found_words']
                        word_highlights = 0
                        
                        for word in found_words:
                            word_instances = page.search_for(word)
                            if word_instances:
                                for inst in word_instances:
                                    highlight = page.add_highlight_annot(inst)
                                    highlight.set_colors(stroke=[1, 0.5, 0], fill=[1, 0.8, 0.4])  # 주황색
                                    highlight.set_opacity(0.3)
                                    highlight.update()
                                    word_highlights += 1
                        
                        if word_highlights > 0:
                            highlighted = True
                            total_highlights += word_highlights
                            print(f"    → 개별 단어 {word_highlights}개 하이라이트")
            
            # 3단계: 핵심 키워드만 별도 하이라이트 (매우 중요한 단어들)
            important_words = [w for w in target_words if len(w) >= 4][:5]  # 4글자 이상, 최대 5개
            
            for word in important_words:
                word_instances = page.search_for(word)
                if word_instances:
                    for inst in word_instances:
                        # 이미 하이라이트된 영역과 겹치는지 확인 (간단한 방법)
                        highlight = page.add_highlight_annot(inst)
                        highlight.set_colors(stroke=[0.5, 0, 0.5], fill=[0.8, 0.6, 0.8])  # 보라색
                        highlight.set_opacity(0.2)
                        highlight.update()
        
        print(f"[완료] 총 {total_highlights}개 하이라이트 적용")
        
        if highlighted:
            # 하이라이트가 적용된 PDF를 새 파일로 저장
            output_path = tempfile.mktemp(suffix='_word_highlighted.pdf')
            doc.save(output_path)
            doc.close()
            print(f"[완료] 하이라이팅 적용된 PDF 저장: {output_path}")
            return output_path
        else:
            doc.close()
            print(f"[실패] 하이라이팅 대상을 찾지 못함")
            return pdf_path
            
    except Exception as e:
        print(f"[오류] PDF 하이라이팅 오류: {str(e)}")
        try:
            doc.close()
        except:
            pass
        return pdf_path

def add_pdf_highlighting(pdf_path, highlight_text):
    """PDF에 텍스트 하이라이팅 추가 (개선된 버전)"""
    try:
        print(f"[하이라이팅 시작] PDF: {pdf_path}, 텍스트: '{highlight_text}'")
        
        # PyMuPDF로 PDF 열기
        doc = fitz.open(pdf_path)
        
        # 하이라이팅할 텍스트 정리
        clean_text = highlight_text.strip()
        if not clean_text:
            print("하이라이팅할 텍스트가 비어있습니다.")
            doc.close()
            return pdf_path
        
        highlighted = False
        
        # 모든 페이지 검색
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            
            # print(f"[페이지 {page_num + 1}] 페이지 텍스트 길이: {len(page_text)}")
            
            page_highlighted = False
            
            # 방법 1: 정확한 텍스트 매칭
            text_instances = page.search_for(clean_text)
            if text_instances:
                for inst in text_instances:
                    highlight = page.add_highlight_annot(inst)
                    highlight.set_colors(stroke=[1, 1, 0], fill=[1, 1, 0])  # 노란색
                    highlight.set_opacity(0.5)
                    highlight.update()
                    highlighted = True
                    page_highlighted = True
                    print(f"[성공] 페이지 {page_num + 1}에서 정확한 텍스트 하이라이트")
                    
            # 정확한 매칭이 성공했어도 다른 방법들도 시도 (더 많은 부분을 찾기 위해)
            
            # 방법 2: 공백과 특수문자를 정규화한 검색 (정확한 매칭이 실패했거나 추가 검색이 필요한 경우)
            if not page_highlighted:
            # 여러 공백, 줄바꿈을 하나의 공백으로 통일
                normalized_page_text = re.sub(r'\s+', ' ', page_text.strip())
                normalized_highlight_text = re.sub(r'\s+', ' ', clean_text.strip())
            
            # 대소문자 구분 없이 검색
            if normalized_highlight_text.lower() in normalized_page_text.lower():
                print(f"[발견] 페이지 {page_num + 1}에서 정규화된 텍스트 발견")
                
                # 원본 텍스트에서 해당 부분의 정확한 위치 찾기
                pattern = re.escape(normalized_highlight_text).replace(r'\ ', r'\s+')
                match = re.search(pattern, page_text, re.IGNORECASE)
                
                if match:
                    start_pos = match.start()
                    end_pos = match.end()
                    matched_text = page_text[start_pos:end_pos]
                    
                    print(f"[매칭된 텍스트] '{matched_text[:100]}...'")
                    
                    # 매칭된 텍스트를 하이라이트
                    highlight_instances = page.search_for(matched_text)
                    if highlight_instances:
                        for inst in highlight_instances:
                            highlight = page.add_highlight_annot(inst)
                            highlight.set_colors(stroke=[1, 1, 0], fill=[1, 1, 0])
                            highlight.set_opacity(0.5)
                            highlight.update()
                            highlighted = True
                            page_highlighted = True
                            print(f"[성공] 페이지 {page_num + 1}에서 정규화 텍스트 하이라이트")
                    else:
                        # 단어별로 나누어서 하이라이트 시도
                        words = matched_text.split()
                        consecutive_found = []
                        
                        for word in words:
                            if len(word.strip()) > 0:
                                word_instances = page.search_for(word.strip())
                                if word_instances:
                                    consecutive_found.extend(word_instances)
                        
                        if consecutive_found:
                            # 연속된 단어들을 하나의 영역으로 합치기
                            min_x0 = min(rect.x0 for rect in consecutive_found)
                            min_y0 = min(rect.y0 for rect in consecutive_found)
                            max_x1 = max(rect.x1 for rect in consecutive_found)
                            max_y1 = max(rect.y1 for rect in consecutive_found)
                            
                            combined_rect = fitz.Rect(min_x0, min_y0, max_x1, max_y1)
                            highlight = page.add_highlight_annot(combined_rect)
                            highlight.set_colors(stroke=[1, 1, 0], fill=[1, 1, 0])
                            highlight.set_opacity(0.5)
                            highlight.update()
                            highlighted = True
                            page_highlighted = True
                            print(f"[성공] 페이지 {page_num + 1}에서 단어 조합 하이라이트")
                continue
            
            # 방법 3: 텍스트를 문장 단위로 나누어서 검색 (항상 시도)
            sentences = re.split(r'[.!?\n]\s*', clean_text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 5]  # 5자 이상 문장만
            
            print(f"[문장 검색] 추출된 문장 수: {len(sentences)}")
            
            for sentence in sentences:
                sentence_normalized = re.sub(r'\s+', ' ', sentence.strip())
                if len(sentence_normalized) < 5:  # 너무 짧은 문장 건너뛰기
                    continue
                    
                if sentence_normalized.lower() in normalized_page_text.lower():
                    pattern = re.escape(sentence_normalized).replace(r'\ ', r'\s+')
                    matches = list(re.finditer(pattern, page_text, re.IGNORECASE))
                    
                    for match in matches:
                        matched_sentence = page_text[match.start():match.end()]
                        sentence_instances = page.search_for(matched_sentence)
                        
                        if sentence_instances:
                            for inst in sentence_instances:
                                highlight = page.add_highlight_annot(inst)
                                highlight.set_colors(stroke=[0, 1, 0], fill=[0.8, 1, 0.8])  # 초록색
                                highlight.set_opacity(0.4)
                                highlight.update()
                                highlighted = True
                                print(f"[성공] 페이지 {page_num + 1}에서 문장 '{sentence_normalized[:30]}...' 하이라이트")
            
            # 방법 4: 핵심 키워드 검색 (마지막 수단, 전체 텍스트를 찾지 못한 경우에만)
            if not highlighted:
                # 의미있는 키워드만 추출 (3글자 이상, 특수 단어 제외)
                keywords = re.findall(r'[\w가-힣]{3,}', clean_text)
                # 일반적인 단어들 제외
                common_words = {'관한', '사항', '업무', '계획', '수립', '관리', '운영', '지원', '개발'}
                keywords = [w for w in keywords if w not in common_words]
                
                print(f"[키워드 검색] 의미있는 키워드: {keywords[:3]}")  # 최대 3개만 표시
                
                # 키워드가 너무 많으면 처음 3개만 사용
                for keyword in keywords[:3]:
                    keyword_instances = page.search_for(keyword)
                    if keyword_instances:
                        for inst in keyword_instances:
                            highlight = page.add_highlight_annot(inst)
                            highlight.set_colors(stroke=[1, 0.5, 0], fill=[1, 0.8, 0])  # 주황색
                            highlight.set_opacity(0.4)
                            highlight.update()
                            highlighted = True
                            print(f"[부분 성공] 페이지 {page_num + 1}에서 키워드 '{keyword}' 하이라이트")
        
        if highlighted:
            # 하이라이트가 적용된 PDF를 새 임시 파일로 저장
            output_path = tempfile.mktemp(suffix='_highlighted.pdf')
            doc.save(output_path)
            doc.close()
            print(f"[완료] 하이라이팅 적용된 PDF 저장: {output_path}")
            return output_path
        else:
            doc.close()
            print(f"[실패] 하이라이팅 대상 텍스트를 찾지 못함")
            return pdf_path
            
    except Exception as e:
        print(f"[오류] PDF 하이라이팅 오류: {str(e)}")
        try:
            doc.close()
        except:
            pass
        return pdf_path

def normalize_text(text):
    """텍스트 정규화 - 인코딩 문제 해결"""
    if not text:
        return ""
    
    # Unicode 정규화
    text = unicodedata.normalize('NFC', text)
    
    # 깨진 문자 패턴 제거/변환
    text = re.sub(r'[�]+', '', text)  # 깨진 문자 제거
    text = re.sub(r'[ᅟᅠ]+', ' ', text)  # 한글 공백 문자 처리
    text = re.sub(r'\s+', ' ', text)  # 연속 공백 정리
    
    return text.strip()

def extract_clean_words(text, min_length=2):
    """깨끗한 단어 추출 - 더 관대한 방식"""
    # 텍스트 정규화
    clean_text = normalize_text(text)
    
    # 괄호 안 내용, 특수문자 정리
    clean_text = re.sub(r'\([^)]*\)', ' ', clean_text)  # 괄호 제거
    clean_text = re.sub(r'[^\w\s가-힣]', ' ', clean_text)  # 특수문자 제거
    
    # 단어 추출
    words = re.findall(r'[가-힣a-zA-Z0-9]{%d,}' % min_length, clean_text)
    
    # 불용어 및 너무 일반적인 단어 제거
    stop_words = {
        '규정', '조항', '시행', '세칙', '학칙', '대학원', '이상', '이하', '포함', '제외',
        '또는', '그리고', '따라서', '다만', '다음', '각호', '해당', '관련',
        '있다', '없다', '한다', '된다', '이다', '아니다', '하여', '의해'
    }
    
    meaningful_words = [w for w in words if w not in stop_words and len(w) >= min_length]
    
    return meaningful_words

def fuzzy_search_in_page(page_text, target_text, threshold=0.6):
    """PDF 페이지에서 유사 텍스트 찾기"""
    results = []
    
    # 페이지 텍스트를 문장/구문 단위로 분할
    segments = re.split(r'[.。!?]\s*|\n\s*', page_text)
    segments = [s.strip() for s in segments if len(s.strip()) > 10]
    
    for segment in segments:
        # 유사도 계산
        similarity = difflib.SequenceMatcher(None, 
                                           normalize_text(target_text.lower()), 
                                           normalize_text(segment.lower())).ratio()
        
        if similarity >= threshold:
            results.append({
                'text': segment,
                'similarity': similarity
            })
    
    return sorted(results, key=lambda x: x['similarity'], reverse=True)

def word_overlap_search(page_text, target_words, min_overlap=0.3):
    """단어 겹치는 정도로 유사 구문 찾기"""
    if not target_words:
        return []
    
    results = []
    segments = re.split(r'[.。!?]\s*|\n\s*', page_text)
    
    for segment in segments:
        if len(segment.strip()) < 5:
            continue
            
        segment_words = extract_clean_words(segment)
        if not segment_words:
            continue
        
        # 단어 겹침 계산
        overlap_count = 0
        for target_word in target_words:
            for segment_word in segment_words:
                # 정확히 일치하거나 하나가 다른 하나를 포함하는 경우
                if (target_word.lower() == segment_word.lower() or
                    target_word.lower() in segment_word.lower() or
                    segment_word.lower() in target_word.lower()):
                    overlap_count += 1
                    break
        
        overlap_ratio = overlap_count / len(target_words)
        
        if overlap_ratio >= min_overlap:
            results.append({
                'text': segment.strip(),
                'overlap_ratio': overlap_ratio,
                'overlap_count': overlap_count
            })
    
    return sorted(results, key=lambda x: x['overlap_ratio'], reverse=True)

def debug_pdf_text_extraction(pdf_path, page_num=0):
    """PDF 텍스트 추출 디버깅"""
    doc = fitz.open(pdf_path)
    if page_num < len(doc):
        page = doc[page_num]
        
        print("=== PDF 텍스트 추출 디버깅 ===")
        
        # 기본 텍스트 추출
        text1 = page.get_text()
        print(f"기본 추출 (길이: {len(text1)}): {text1[:200]}...")
        
        # dict 형태로 추출
        text_dict = page.get_text("dict")
        print(f"Dict 추출 블록 수: {len(text_dict['blocks'])}")
        
        # 블록별 텍스트
        for i, block in enumerate(text_dict['blocks'][:3]):  # 처음 3개만
            if 'lines' in block:
                block_text = ""
                for line in block['lines']:
                    for span in line['spans']:
                        block_text += span['text'] + " "
                print(f"블록 {i}: {block_text.strip()[:100]}...")
    
    doc.close()

def add_pdf_highlighting_robust(pdf_path, highlight_text, debug=True):
    """강화된 PDF 하이라이팅 - 인코딩/텍스트 문제 해결"""
    try:
        if debug:
            print(f"=== 하이라이팅 디버그 모드 ===")
            print(f"원본 텍스트: {highlight_text}")
            debug_pdf_text_extraction(pdf_path, 0)
        
        doc = fitz.open(pdf_path)
        
        # 타겟 텍스트 전처리
        clean_target = normalize_text(highlight_text)
        target_words = extract_clean_words(clean_target)
        
        print(f"정규화된 텍스트: {clean_target}")
        print(f"추출된 핵심 단어: {target_words}")
        
        if not target_words:
            print("추출할 단어가 없습니다.")
            doc.close()
            return pdf_path
        
        highlighted = False
        total_highlights = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 다양한 방법으로 텍스트 추출
            methods = {
                'basic': page.get_text(),
                'blocks': page.get_text("blocks"),
                'dict': page.get_text("dict")
            }
            
            page_highlighted = False
            
            for method_name, extracted_text in methods.items():
                if method_name == 'dict':
                    # dict 방식은 별도 처리
                    page_text = ""
                    for block in extracted_text['blocks']:
                        if 'lines' in block:
                            for line in block['lines']:
                                for span in line['spans']:
                                    page_text += span['text'] + " "
                    extracted_text = page_text
                elif method_name == 'blocks':
                    extracted_text = " ".join(str(block) for block in extracted_text if isinstance(block, str))
                
                if not extracted_text:
                    continue
                
                print(f"\n[페이지 {page_num + 1}] {method_name} 방식으로 추출된 텍스트 길이: {len(extracted_text)}")
                
                # 방법 1: 직접 텍스트 매칭
                normalized_page = normalize_text(extracted_text)
                if clean_target.lower() in normalized_page.lower():
                    # 원본에서 해당 부분 찾기
                    instances = page.search_for(clean_target)
                    if instances:
                        for inst in instances:
                            highlight = page.add_highlight_annot(inst)
                            highlight.set_colors(stroke=[1, 0, 0], fill=[1, 0.8, 0.8])
                            highlight.set_opacity(0.7)
                            highlight.update()
                            highlighted = True
                            page_highlighted = True
                            total_highlights += 1
                        print(f"  ✓ 직접 매칭 성공: {len(instances)}개")
                        continue
                
                # 방법 2: 유사 텍스트 검색
                similar_texts = fuzzy_search_in_page(extracted_text, clean_target, 0.5)
                for similar in similar_texts[:2]:  # 상위 2개만
                    instances = page.search_for(similar['text'])
                    if instances:
                        for inst in instances:
                            highlight = page.add_highlight_annot(inst)
                            highlight.set_colors(stroke=[0, 1, 0], fill=[0.8, 1, 0.8])
                            highlight.set_opacity(0.5)
                            highlight.update()
                            highlighted = True
                            page_highlighted = True
                            total_highlights += 1
                        print(f"  ✓ 유사 매칭 성공: {similar['similarity']:.2f}")
                
                # 방법 3: 단어 겹침 검색
                word_matches = word_overlap_search(extracted_text, target_words, 0.3)
                for match in word_matches[:3]:  # 상위 3개만
                    instances = page.search_for(match['text'])
                    if instances:
                        for inst in instances:
                            highlight = page.add_highlight_annot(inst)
                            highlight.set_colors(stroke=[0, 0, 1], fill=[0.8, 0.8, 1])
                            highlight.set_opacity(0.4)
                            highlight.update()
                            highlighted = True
                            page_highlighted = True
                            total_highlights += 1
                        print(f"  ✓ 단어 겹침 매칭: {match['overlap_ratio']:.1%}")
                
                if page_highlighted:
                    break  # 이 페이지에서 매칭 성공했으면 다음 방법은 시도하지 않음
        
        print(f"\n=== 결과 ===")
        print(f"총 {total_highlights}개 하이라이트 적용")
        
        if highlighted:
            output_path = tempfile.mktemp(suffix='_robust_highlighted.pdf')
            doc.save(output_path)
            doc.close()
            print(f"하이라이팅 완료: {output_path}")
            return output_path
        else:
            doc.close()
            print("하이라이팅할 내용을 찾지 못했습니다.")
            
            # 디버그 정보 추가 출력
            print("\n=== 디버그 권장사항 ===")
            print("1. PDF의 첫 페이지 텍스트를 확인하세요:")
            print("   debug_pdf_text_extraction(pdf_path)")
            print("2. 원본 텍스트가 올바른지 확인하세요")
            print("3. 단어 추출 결과를 확인하세요:")
            print(f"   추출된 단어들: {target_words}")
            
            return pdf_path
            
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        try:
            doc.close()
        except:
            pass
        return pdf_path

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