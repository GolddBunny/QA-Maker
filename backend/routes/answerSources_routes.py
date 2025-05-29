from flask import Blueprint, request, jsonify
import re
import os
import pandas as pd
from typing import List, Dict, Optional
from firebase_config import bucket
from io import BytesIO

url_source_bp = Blueprint('url_source', __name__)

def extract_sources_from_answer(answer_text: str) -> List[int]:
    """답변 텍스트에서 Sources 번호 추출"""
    sources_match = re.search(r'Sources[\s:：]*\(?([\d,\s]+)\)?', answer_text, re.IGNORECASE)
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

def find_url_and_title_from_source_id(df: pd.DataFrame, source_id: int) -> Optional[Dict[str, str]]:
    """DataFrame에서 source_id에 해당하는 URL과 Title 추출 (다양한 형태 지원)"""
    try:
        print("find url and title from source id")
        row = df[df['human_readable_id'] == source_id]
        print("row ", row)
        
        if not row.empty:
            text = row.iloc[0]['text']
            print("row text[0]: ", text)
            
            # 패턴 수정: URL 뒤에 Markdown이나 다른 텍스트가 오는 경우 처리
            # Title과 URL Source 사이에 줄바꿈이 없는 경우
            combined_match = re.search(r'Title:\s*([^U]+?)URL Source:\s*(https?://[^\s]+?)(?:Markdown|$|\s)', text)
            
            title_match = None
            url_match = None
            
            if combined_match:
                title_match = type('Match', (), {'group': lambda self, n: combined_match.group(1).strip()})()
                url_match = type('Match', (), {'group': lambda self, n: combined_match.group(2).strip()})()
            else:
                # 대안 패턴: 각각 따로 찾기
                title_match_regex = re.search(r'Title:\s*([^U\n]+)', text)
                url_match_regex = re.search(r'URL Source:\s*(https?://[^\s]+?)(?:Markdown|$|\s)', text)
                
                if title_match_regex:
                    title_match = type('Match', (), {'group': lambda self, n: title_match_regex.group(1).strip()})()
                if url_match_regex:
                    url_match = type('Match', (), {'group': lambda self, n: url_match_regex.group(2).strip()})()
            
            print("title_match: ", title_match)
            print("url_match: ", url_match)
            
            # 현재 행에서 찾았으면 반환
            if title_match and url_match:
                title = title_match.group(1).strip()
                # title이 20글자 넘으면 줄이기
                if len(title) > 20:
                    title = title[:20] + "..."
                return {
                    'title': title,
                    'url': url_match.group(1).strip()
                }
            
            # fallback: 이전 행들에서 탐색
            for i in range(1, 5):
                prev_id = source_id - i
                prev_row = df[df['human_readable_id'] == prev_id]
                if not prev_row.empty:
                    prev_text = prev_row.iloc[0]['text']
                    print(f"fallback row text[{prev_id}]: ", prev_text)
                    
                    # 동일한 패턴으로 이전 행에서도 찾기
                    prev_combined_match = re.search(r'Title:\s*([^U]+?)URL Source:\s*(https?://[^\s]+?)(?:Markdown|$|\s)', prev_text)
                    
                    prev_title_match = None
                    prev_url_match = None
                    
                    if prev_combined_match:
                        prev_title_match = type('Match', (), {'group': lambda self, n: prev_combined_match.group(1).strip()})()
                        prev_url_match = type('Match', (), {'group': lambda self, n: prev_combined_match.group(2).strip()})()
                    else:
                        # 대안 패턴
                        prev_title_match_regex = re.search(r'Title:\s*([^U\n]+)', prev_text)
                        prev_url_match_regex = re.search(r'URL Source:\s*(https?://[^\s]+?)(?:Markdown|$|\s)', prev_text)
                        
                        if prev_title_match_regex:
                            prev_title_match = type('Match', (), {'group': lambda self, n: prev_title_match_regex.group(1).strip()})()
                        if prev_url_match_regex:
                            prev_url_match = type('Match', (), {'group': lambda self, n: prev_url_match_regex.group(2).strip()})()
                    
                    print(f"fallback title_match[{prev_id}]: ", prev_title_match)
                    print(f"fallback url_match[{prev_id}]: ", prev_url_match)
                    
                    if prev_title_match and prev_url_match:
                        title = prev_title_match.group(1).strip()
                        # title이 20글자 넘으면 줄이기
                        if len(title) > 20:
                            title = title[:20] + "..."
                        return {
                            'title': title,
                            'url': prev_url_match.group(1).strip()
                        }
            
            # 부분적으로라도 찾은 경우 반환
            title = title_match.group(1).strip() if title_match else None
            if title and len(title) > 20:
                title = title[:20] + "..."
            return {
                'title': title,
                'url': url_match.group(1).strip() if url_match else None
            }
        
        return None
        
    except Exception as e:
        print(f"Error in find_url_and_title_from_source_id: {e}")
        return None

@url_source_bp.route('/extract-sources', methods=['POST'])
def extract_sources():
    data = request.get_json()

    if not data or 'answer' not in data or 'page_id' not in data:
        return jsonify({'error': '필수 파라미터가 누락되었습니다.'}), 400

    answer_text = data['answer']
    page_id = data['page_id']

    # Sources 번호 추출
    source_ids = extract_sources_from_answer(answer_text)
    print(f"[DEBUG] 추출된 source_ids: {source_ids}")

    if not source_ids:
        return jsonify({'sources': []})

    # Firebase Storage에서 Parquet 파일 직접 읽기
    blob_path = f'pages/{page_id}/results/text_units.parquet'
    blob = bucket.blob(blob_path)

    print("blob path: ", blob_path)
    if not blob.exists():
        return jsonify({'error': f'Firebase Storage에서 Parquet 파일을 찾을 수 없습니다: {blob_path}'}), 404

    parquet_bytes = blob.download_as_bytes()
    parquet_stream = BytesIO(parquet_bytes)
    df = pd.read_parquet(parquet_stream)

    # 각 소스 ID에 대한 URL과 Title 찾기
    results = []
    for source_id in source_ids:
        source_info = find_url_and_title_from_source_id(df, source_id)
        if source_info and (source_info['url'] or source_info['title']):
            result = {'source_id': source_id}
            print("source id: ", result)
            if source_info['title']:
                result['title'] = source_info['title']
                print("title ", result['title'])
            if source_info['url']:
                result['url'] = source_info['url']
                print("url ", result['url'])
            results.append(result)
            print("results: ", results)
    return jsonify({'sources': results})