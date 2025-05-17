from flask import Blueprint, jsonify, send_file, request
import os
import csv
import re
import urllib.parse

source_bp = Blueprint('source', __name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
CSV_PATH = os.path.join(PROJECT_ROOT, 'context_data_sources.csv')

@source_bp.route('/api/context-sources', methods=['GET'])
def get_context_sources():
    """CSV 파일에서 추출한 headline 반환"""
    try:
        # 요청에서 page_id 파라미터 가져오기
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400
            
        headlines = set()  # 중복 제거
        
        if not os.path.exists(CSV_PATH):
            return jsonify({"error": f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}"}), 404
            
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            for row in csv_reader:
                # headline 처리
                if 'text' in row and row['text']:
                    # headline 추출 시도
                    headline = extract_headline(row['text'])
                    if headline:
                        headlines.add(headline)
                        
                # headline 필드가 있는 경우
                elif 'headline' in row and row['headline'].strip():
                    headlines.add(row['headline'].strip())
                    
        return jsonify({
            "headlines": list(headlines),
        })
        
    except Exception as e:
        print(f"CSV 처리 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500

def extract_headline(text):
    """텍스트에서 headline 정보 추출"""
    if not text or not isinstance(text, str):
        return None
        
    try:
        # 방법 1: headline: 뒤에 오는 모든 텍스트 추출
        headline_match = re.search(r'headline:\s*([^page:|content:|headline:|\n]+)', text, re.IGNORECASE)
        if headline_match and headline_match.group(1):
            return headline_match.group(1).strip()
            
        # 방법 2: 줄바꿈으로만 구분
        headline_match = re.search(r'headline:\s*([^\n]+)', text, re.IGNORECASE)
        if headline_match and headline_match.group(1):
            headline = headline_match.group(1).strip()
            # 다음 메타데이터가 있으면 그 전까지만 추출
            next_meta_match = re.search(r'\s+(?:content:|page:)', headline, re.IGNORECASE)
            if next_meta_match:
                headline = headline[:next_meta_match.start()].strip()
            return headline
            
        return None
    except Exception as e:
        print(f"headline 추출 중 오류: {str(e)}")
        return None

@source_bp.route('/api/pdf/<path:filename>')
def get_pdf(filename):
    """PDF 파일 제공"""
    try:
        # 요청에서 page_id 파라미터 가져오기
        page_id = request.args.get('page_id')
        if not page_id:
            return jsonify({"error": "page_id가 제공되지 않았습니다"}), 400
            
        decoded_filename = urllib.parse.unquote(filename) # URL 디코딩 - 한글 파일명 처리
        # 동적 DATA_DIR 경로 구성 (page_id 사용)
        DATA_DIR = os.path.join(PROJECT_ROOT, f'data/input/{page_id}/input')
        
        file_path = os.path.join(DATA_DIR, f"{decoded_filename}.pdf")
        
        if not os.path.exists(file_path):
            return jsonify({"error": f"파일을 찾을 수 없습니다: {decoded_filename}.pdf"}), 404
            
        return send_file(file_path, mimetype='application/pdf')
    except Exception as e:
        print(f"PDF 제공 중 오류: {str(e)}")
        return jsonify({"error": str(e)}), 500