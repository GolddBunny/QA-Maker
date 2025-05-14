import requests
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime

# tqdm 조건부 임포트 (설치되어 있지 않을 경우 대비)
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # tqdm이 없을 경우 대체 함수 정의
    def tqdm(iterable, **kwargs):
        total = len(iterable)
        for i, item in enumerate(iterable):
            if i % 5 == 0 or i + 1 == total:  # 5개마다 또는 마지막 항목에 진행 상황 출력
                print(f"진행 중: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
            yield item

def jina_crawling(crawl_url, output_dir):
    """단일 URL을 Jina를 통해 크롤링합니다.
    
    Args:
        crawl_url: 크롤링할 URL
        output_dir: 결과를 저장할 디렉토리 경로
        
    Returns:
        str: 저장된 파일 경로
    """
    # 이미 완전한 URL인지 확인
    if crawl_url.startswith(('http://', 'https://')):
        url = f"https://r.jina.ai/{crawl_url}"
    else:
        url = f"https://r.jina.ai/{crawl_url}"
    
    # headers = {"Authorization": "Bearer jina_5767c25060bb48d0885ef1593dfa3976y4jp4QeAhiM45-Y1ACLiyx_y8GQG", "X-Md-Heading-Style": "setext", "X-Remove-Selector": "header, .class, #id, a href, href, popup"}
    headers = {"Authorization": "Bearer jina_5767c25060bb48d0885ef1593dfa3976y4jp4QeAhiM45-Y1ACLiyx_y8GQG"}
    response = requests.get(url, headers=headers)
    
    parsed_url = urlparse(url)
    
    # Title 추출 시도
    title = None
    try:
        # response.text에서 Title: 다음에 오는 텍스트 추출
        title_match = re.search(r'Title:\s*(.*?)(?:\n|$)', response.text)
        if title_match:
            title = title_match.group(1).strip()
            # 파일명으로 사용할 수 있도록 특수문자 제거 및 길이 제한
            title = re.sub(r'[\\/*?:"<>|]', '', title)  # 파일명에 사용할 수 없는 문자 제거
            if len(title) > 50:  # 제목이 너무 길면 자르기
                title = title[:50]
    except:
        title = None
    
    # 파일명 생성 (날짜 없이 제목만 사용)
    if title:
        filename = f"{title}.txt"
    else:
        # 원본 URL에서 페이지 이름 추출 시도
        try:
            page_name = crawl_url.split('/')[-1].split('.')[0]
            if page_name:
                filename = f"{page_name}.txt"
            else:
                # URL의 마지막 부분을 사용하여 파일명 생성
                url_parts = crawl_url.split('/')
                last_part = url_parts[-1] if url_parts[-1] else url_parts[-2]
                filename = f"{last_part}.txt"
        except:
            # URL에서 도메인 이름 추출하여 파일명으로 사용
            domain = parsed_url.netloc.split('.')[0]
            filename = f"{domain}.txt"
    
    # 폴더 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일 경로
    file_path = output_dir / filename
    
    # 파일명 중복 처리
    counter = 1
    original_path = file_path
    while file_path.exists():
        # 파일이 이미 존재하면 이름 뒤에 숫자 추가
        stem = original_path.stem
        file_path = output_dir / f"{stem}_{counter}.txt"
        counter += 1
    
    print(f"크롤링 결과 저장 경로: {file_path}")
    
    # 응답 내용 파일로 저장
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    return str(file_path)

def batch_jina_crawling(url_list_file, delay=1.0):
    """URL 목록 파일에서 URL을 읽어 일괄적으로 크롤링합니다.
    
    Args:
        url_list_file: URL 목록이 저장된 파일 경로
        delay: 요청 간 지연 시간(초), 기본값 1.0
        
    Returns:
        list: 저장된 파일 경로 목록
    """
    url_file_path = Path(url_list_file)
    
    if not url_file_path.exists():
        print(f"URL 목록 파일을 찾을 수 없습니다: {url_file_path}")
        return []
    
    # URL 리스트 파일 이름에서 확장자를 제외한 이름으로 폴더 생성
    url_file_name = url_file_path.stem  # 확장자 제외한 파일명
    
    # 출력 디렉토리 설정 - 파일 이름과 동일한 폴더
    output_dir = Path(__file__).parent.parent.parent / "data" / "crawling" / "jina_crawling" / url_file_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"크롤링 결과 저장 폴더: {output_dir}")
    
    # URL 목록 파일 읽기
    with open(url_file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    print(f"총 {len(urls)}개의 URL을 크롤링합니다.")
    
    saved_files = []
    
    # 진행 상황 표시
    progress_iter = tqdm(urls, desc="URL 크롤링 중") if TQDM_AVAILABLE else urls
    
    for i, url in enumerate(progress_iter):
        try:
            if not TQDM_AVAILABLE and i % 5 == 0:
                print(f"진행 중: {i+1}/{len(urls)} ({(i+1)/len(urls)*100:.1f}%)")
                
            file_path = jina_crawling(url, output_dir)
            saved_files.append(file_path)
            
            # 요청 간 지연 시간 추가
            time.sleep(delay)
            
        except Exception as e:
            print(f"URL 크롤링 실패: {url}, 오류: {e}")
    
    print(f"크롤링 완료: {len(saved_files)}/{len(urls)} URL 처리됨")
    return saved_files


if __name__ == "__main__":
    # 시작 시간 기록
    start_time = datetime.now()
    print(f"프로그램 실행 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # URL 리스트 파일에서 일괄 크롤링
    data_dir = Path(__file__).parent.parent.parent / "data" / "crawling"
    url_list_file = data_dir / "20250511_0100_hansung_ac_kr_hansung" / "page_urls_20250511_0100.txt"
    batch_jina_crawling(url_list_file)
    
    # 종료 시간 기록 및 실행 시간 계산
    end_time = datetime.now()
    execution_time = end_time - start_time
    
    print(f"프로그램 실행 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 실행 시간: {execution_time}")