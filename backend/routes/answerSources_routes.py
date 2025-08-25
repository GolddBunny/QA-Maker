from flask import Blueprint, request, jsonify
import re
import os
import pandas as pd
from typing import List, Dict, Optional
from firebase_config import bucket
from io import BytesIO

url_source_bp = Blueprint('url_source', __name__)

def extract_urls_from_csv(csv_path: str) -> List[Dict[str, str]]:
    """CSV 파일에서 URL Source와 Title 추출"""
    try:
        print(f"[DEBUG] CSV 파일 경로 확인: {csv_path}")
        
        if not os.path.exists(csv_path):
            print(f"[ERROR] CSV 파일이 존재하지 않습니다: {csv_path}")
            # 현재 디렉토리와 상위 디렉토리에서 파일 찾기
            alternative_paths = [
                "./context_data_sources.csv",
                "../context_data_sources.csv", 
                "context_data_sources.csv",
                "./backend/context_data_sources.csv"
            ]
            
            for alt_path in alternative_paths:
                if os.path.exists(alt_path):
                    print(f"[INFO] 대체 경로에서 파일 발견: {alt_path}")
                    csv_path = alt_path
                    break
            else:
                print(f"[ERROR] 모든 경로에서 CSV 파일을 찾을 수 없습니다")
                return []
        
        print(f"[DEBUG] CSV 파일 읽기 시작: {csv_path}")
        
        # CSV 파일 읽기 (여러 인코딩 시도)
        df = None
        encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'latin-1']
        
        for encoding in encodings:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                print(f"[DEBUG] CSV 파일 읽기 성공 (인코딩: {encoding})")
                break
            except UnicodeDecodeError:
                print(f"[DEBUG] {encoding} 인코딩 실패, 다음 인코딩 시도...")
                continue
            except Exception as e:
                print(f"[DEBUG] CSV 읽기 오류 ({encoding}): {e}")
                continue
        
        if df is None:
            print("[ERROR] 모든 인코딩으로 CSV 파일 읽기 실패")
            return []
        
        print(f"[DEBUG] CSV 파일 정보:")
        print(f"  - 행 수: {len(df)}")
        print(f"  - 컬럼 수: {len(df.columns)}")
        print(f"  - 컬럼명: {list(df.columns)}")
        
        urls = []
        
        for idx, row in df.iterrows():
            try:
                # 각 컬럼에서 텍스트 찾기 (컬럼명에 관계없이 모든 컬럼 검사)
                text = ""
                for col in df.columns:
                    if pd.notna(row[col]):
                        text += str(row[col]) + " "
                
                if not text.strip():
                    continue
                
                # 첫 몇 행의 데이터 출력 (디버깅용)
                if idx < 3:
                    print(f"[DEBUG] 행 {idx} 텍스트 (처음 200자): {text[:200]}...")
                
                # Title 추출 (여러 패턴 시도)
                title = None
                title_patterns = [
                    r'Title:\s*([^\n\r]+?)(?=\s*URL Source:|\s*Markdown Content:|\n|\r|$)',
                    r'Title:\s*([^\n\r]+)',
                    r'^([^\n\r]+?)(?=\s*URL Source:)',
                ]
                
                for pattern in title_patterns:
                    title_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                    if title_match:
                        title = title_match.group(1).strip()
                        if title and title != "Title:":
                            break
                
                # URL Source 추출 (여러 패턴 시도)
                url = None
                url_patterns = [
                    r'URL Source:\s*(https?://[^\s\n\r]+)',
                    r'URL:\s*(https?://[^\s\n\r]+)',
                    r'Source:\s*(https?://[^\s\n\r]+)',
                    r'(https?://[^\s\n\r]+)'
                ]
                
                for pattern in url_patterns:
                    url_match = re.search(pattern, text, re.IGNORECASE)
                    if url_match:
                        url = url_match.group(1).strip()
                        break
                
                if idx < 3:  # 처음 3개 행 디버깅 정보
                    print(f"[DEBUG] 행 {idx} 추출 결과: Title='{title}', URL='{url}'")
                
                if url:  # URL이 있는 경우만 추가
                    # 제목이 너무 길면 줄임
                    if title and len(title) > 30:
                        title = title[:30] + "..."
                    
                    url_info = {
                        'title': title or 'URL 링크',
                        'url': url
                    }
                    urls.append(url_info)
                    print(f"[SUCCESS] 추출된 URL #{len(urls)}: {url}, Title: {title}")
                    
            except Exception as e:
                print(f"[ERROR] 행 {idx} 처리 중 오류: {e}")
                continue
        
        print(f"[FINAL] 총 {len(urls)}개의 URL 추출 완료")
        return urls
        
    except Exception as e:
        print(f"[ERROR] CSV 파일 처리 중 전체 오류: {e}")
        import traceback
        traceback.print_exc()
        return []

@url_source_bp.route('/extract-sources-from-csv', methods=['POST'])
def extract_sources_from_csv():
    """CSV 파일에서 모든 URL Source 추출"""
    try:
        # CSV 파일 경로들 (여러 경로 시도)
        possible_paths = [
            "/Users/sunmay/Desktop/Domain_QA_Gen/backend/context_data_sources.csv",
            "./context_data_sources.csv",
            "../context_data_sources.csv", 
            "context_data_sources.csv",
            "./backend/context_data_sources.csv"
        ]
        
        print("[DEBUG] CSV 파일 경로 탐색 시작")
        csv_path = None
        for path in possible_paths:
            print(f"[DEBUG] 경로 확인: {path}")
            if os.path.exists(path):
                csv_path = path
                print(f"[SUCCESS] CSV 파일 발견: {path}")
                break
        
        if not csv_path:
            print("[ERROR] 모든 경로에서 CSV 파일을 찾을 수 없습니다")
            return jsonify({
                'error': 'CSV 파일을 찾을 수 없습니다',
                'searched_paths': possible_paths
            }), 404
        
        # 파일 내용 직접 읽기 시도 (디버깅)
        print(f"[DEBUG] 파일 내용 미리보기 (처음 1000자):")
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                content = f.read(1000)
                print(content)
                print("[DEBUG] --- 미리보기 끝 ---")
        except Exception as preview_error:
            print(f"[DEBUG] 파일 미리보기 실패: {preview_error}")
        
        # CSV에서 URL 추출
        sources = extract_urls_from_csv(csv_path)
        
        return jsonify({
            'sources': sources,
            'total_count': len(sources),
            'csv_path': csv_path
        })
        
    except Exception as e:
        print(f"[ERROR] CSV에서 소스 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'CSV 소스 추출 실패: {str(e)}'}), 500

# 기존 함수들은 호환성을 위해 유지
def extract_sources_from_answer(answer_text: str) -> List[int]:
    """답변 텍스트에서 Sources 번호 추출 (호환성을 위해 유지)"""
    sources_match = re.search(r'Sources[\s:：]*\(?([\d,\s]+)\)?', answer_text, re.IGNORECASE)
    if not sources_match:
        return []
        
    sources_str = sources_match.group(1)
    sources = []
    for part in sources_str.split(','):
        part = part.strip()
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
    """DataFrame에서 source_id에 해당하는 URL과 Title 추출 (호환성을 위해 유지)"""
    try:
        print("find url and title from source id")
        row = df[df['human_readable_id'] == source_id]
        print("row ", row)
        
        def extract_title_url(text: str) -> Optional[Dict[str, str]]:
            combined_match = re.search(r'Title:\s*([^U]+?)URL Source:\s*(https?://[^\s]+?)(?:Markdown|$|\s)', text)
            if combined_match:
                title = combined_match.group(1).strip()
                url = combined_match.group(2).strip()
                return {'title': title, 'url': url}

            title_match = re.search(r'Title:\s*([^U\n]+)', text)
            url_match = re.search(r'URL Source:\s*(https?://[^\s]+?)(?:Markdown|$|\s)', text)
            if title_match or url_match:
                title = title_match.group(1).strip() if title_match else None
                url = url_match.group(1).strip() if url_match else None
                return {'title': title, 'url': url}

            return None
        
        if not row.empty:
            text = row.iloc[0]['text']
            print("row text[0]: ", text)
            result = extract_title_url(text)

            if result and result.get('title') and result.get('url'):
                title = result['title']
                if len(title) > 20:
                    title = title[:20] + "..."
                return {'title': title, 'url': result['url'], 'fallback': False}

        for i in range(1, 1):
            prev_id = source_id - i
            prev_row = df[df['human_readable_id'] == prev_id]
            if not prev_row.empty:
                prev_text = prev_row.iloc[0]['text']
                print(f"fallback row text[{prev_id}]: ", prev_text)
                result = extract_title_url(prev_text)

                if result and result.get('title') and result.get('url'):
                    title = result['title']
                    if len(title) > 20:
                        title = title[:20] + "..."
                    return {'title': title, 'url': result['url'], 'fallback': True}

        result = extract_title_url(text) if not row.empty else None
        title = result['title'] if result and result.get('title') else None
        url = result['url'] if result and result.get('url') else None
        if title and len(title) > 20:
            title = title[:20] + "..."
        if title or url:
            return {'title': title, 'url': url, 'fallback': False}
        
        return None

    except Exception as e:
        print(f"Error in find_url_and_title_from_source_id: {e}")
        return None

@url_source_bp.route('/extract-sources', methods=['POST'])
def extract_sources():
    """기존 방식 (호환성을 위해 유지)"""
    data = request.get_json()

    if not data or 'answer' not in data or 'page_id' not in data:
        return jsonify({'error': '필수 파라미터가 누락되었습니다.'}), 400

    answer_text = data['answer']
    page_id = data['page_id']

    source_ids = extract_sources_from_answer(answer_text)
    print(f"[DEBUG] 추출된 source_ids: {source_ids}")

    if not source_ids:
        return jsonify({'sources': []})

    blob_path = f'pages/{page_id}/results/text_units.parquet'
    blob = bucket.blob(blob_path)

    print("blob path: ", blob_path)
    if not blob.exists():
        return jsonify({'error': f'Firebase Storage에서 Parquet 파일을 찾을 수 없습니다: {blob_path}'}), 404

    parquet_bytes = blob.download_as_bytes()
    parquet_stream = BytesIO(parquet_bytes)
    df = pd.read_parquet(parquet_stream)

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