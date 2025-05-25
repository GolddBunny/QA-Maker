from flask import Blueprint, request, jsonify
import re
import os
import pandas as pd
from typing import List, Dict, Optional

url_source_bp = Blueprint('url_source', __name__)

def extract_sources_from_answer(answer_text: str) -> List[int]:
    """답변 텍스트에서 Sources 번호 추출"""
    sources_match = re.search(r'Sources\s*\(([^)]+)\)', answer_text)
    if not sources_match:
        return []
        
    sources_str = sources_match.group(1)
    # 쉼표로 구분된 숫자 추출
    sources = []
    for part in sources_str.split(','):
        part = part.strip()
        # 범위 처리 (예: 22-24)
        if '-' in part:
            start, end = map(int, part.split('-'))
            sources.extend(range(start, end + 1))
        else:
            try:
                sources.append(int(part))
            except ValueError:
                continue
        
    return sources

def find_url_and_title_from_source_id(parquet_path: str, source_id: int) -> Optional[Dict[str, str]]:
    """Parquet 파일에서 source_id에 해당하는 URL과 Title 추출"""
    try:
        # Parquet 파일 로드
        df = pd.read_parquet(parquet_path)
        
        # human_readable_id가 source_id와 일치하는 행 찾기
        row = df[df['human_readable_id'] == source_id]
        
        if not row.empty:
            text = row.iloc[0]['text']
            
            # Title 추출
            title_match = re.search(r'Title:\s*([^\n]+)', text)
            title = title_match.group(1).strip() if title_match else None
            
            # URL 추출
            url_match = re.search(r'URL Source:\s*(https?://[^\s\n]+)', text)
            url = url_match.group(1).strip() if url_match else None
            
            if title or url:  # 둘 중 하나라도 있으면 반환
                return {
                    'title': title,
                    'url': url
                }
                        
        # 일치하는 데이터가 없으면 ID를 하나씩 줄여가며 찾기
        for i in range(1, 3):  # 최대 5개까지 줄여서 찾기
            prev_id = source_id - i
            row = df[df['human_readable_id'] == prev_id]
            if not row.empty:
                text = row.iloc[0]['text']
                
                # Title 추출
                title_match = re.search(r'Title:\s*([^\n]+)', text)
                title = title_match.group(1).strip() if title_match else None
                
                # URL 추출
                url_match = re.search(r'URL Source:\s*(https?://[^\s\n]+)', text)
                url = url_match.group(1).strip() if url_match else None
                
                if title or url:  # 둘 중 하나라도 있으면 반환
                    return {
                        'title': title,
                        'url': url
                    }
                        
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

@url_source_bp.route('/extract-sources', methods=['POST'])
def extract_sources():
    data = request.get_json()
        
    if not data or 'answer' not in data or 'page_id' not in data:
        return jsonify({'error': '필수 파라미터가 누락되었습니다.'}), 400
        
    answer_text = data['answer']
    page_id = data['page_id']
        
    # config에서 base_dir 가져오기 또는 기본값 사용
    base_dir = os.environ.get('BASE_DIR', '/Users/sunmay/Desktop/Domain_QA_Gen/data/input')
        
    # Sources 번호 추출
    source_ids = extract_sources_from_answer(answer_text)
        
    if not source_ids:
        return jsonify({'sources': []})
        
    # Parquet 파일 경로
    parquet_path = os.path.join(base_dir, page_id, 'output', 'text_units.parquet')
        
    if not os.path.exists(parquet_path):
        return jsonify({'error': f'Parquet 파일을 찾을 수 없습니다: {parquet_path}'}), 404
        
    # 각 소스 ID에 대한 URL과 Title 찾기
    results = []
    for source_id in source_ids:
        source_info = find_url_and_title_from_source_id(parquet_path, source_id)
        if source_info and (source_info['url'] or source_info['title']):  # URL이나 Title 중 하나라도 있으면 결과에 추가
            result = {
                'source_id': source_id
            }
            if source_info['title']:
                result['title'] = source_info['title']
            if source_info['url']:
                result['url'] = source_info['url']
            results.append(result)
        
    return jsonify({'sources': results})