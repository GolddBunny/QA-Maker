import requests
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime
import concurrent.futures
import random
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jina_crawling.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("jina_crawler")

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
            if i % 10 == 0 or i + 1 == total:  # 10개마다 또는 마지막 항목에 진행 상황 출력
                print(f"진행 중: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
            yield item

def jina_crawling(crawl_url, output_dir, verbose=False):
    """단일 URL을 Jina를 통해 크롤링합니다.
    
    Args:
        crawl_url: 크롤링할 URL
        output_dir: 결과를 저장할 디렉토리 경로
        verbose: 상세 로그 출력 여부
        
    Returns:
        str: 저장된 파일 경로
    """
    # 이미 완전한 URL인지 확인
    if crawl_url.startswith(('http://', 'https://')):
        url = f"https://r.jina.ai/{crawl_url}"
    else:
        url = f"https://r.jina.ai/{crawl_url}"
    
    headers = {
    "Authorization": "Bearer jina_5767c25060bb48d0885ef1593dfa3976y4jp4QeAhiM45-Y1ACLiyx_y8GQG",
    "X-Md-Heading-Style": "setext",
    "X-Remove-Selector": ".class, #id, footer, a href",
    "X-Retain-Images": "none",
    "X-Return-Format": "markdown"
    }
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
    
    # 파일명 생성
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
    
    # 상세 로그 설정에 따라 저장 경로 출력
    if verbose:
        logger.info(f"크롤링 결과 저장 경로: {file_path}")
    
    # 응답 내용 파일로 저장
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    return str(file_path)

def process_single_url(url, output_dir, delay_range=(0.5, 1.5), verbose=False):
    """단일 URL을 처리하는 함수로, 스레드 풀에서 호출됩니다.
    
    Args:
        url: 크롤링할 URL
        output_dir: 결과를 저장할 디렉토리 경로
        delay_range: 요청 후 대기할 시간 범위 (최소, 최대)
        verbose: 상세 로그 출력 여부
        
    Returns:
        tuple: (성공 여부, 결과 또는 오류 메시지)
    """
    try:
        # 요청 간 무작위 지연 시간 추가 (API 제한 방지)
        delay = random.uniform(*delay_range)
        time.sleep(delay)
        
        file_path = jina_crawling(url, output_dir, verbose)
        return True, file_path
    except Exception as e:
        error_msg = f"URL 크롤링 실패: {url}, 오류: {e}"
        logger.error(error_msg)
        return False, error_msg

def batch_jina_crawling(url_list_file, max_workers=5, delay_range=(0.5, 1.5), verbose=False):
    """URL 목록 파일에서 URL을 읽어 병렬로 크롤링합니다.
    
    Args:
        url_list_file: URL 목록이 저장된 파일 경로
        max_workers: 동시에 실행할 최대 작업자 수, 기본값 5
        delay_range: 요청 간 지연 시간 범위 (최소, 최대)
        verbose: 상세 로그 출력 여부 (True: 모든 로그 출력, False: 요약 정보만 출력)
        
    Returns:
        list: 저장된 파일 경로 목록
    """
    url_file_path = Path(url_list_file)
    
    if not url_file_path.exists():
        logger.error(f"URL 목록 파일을 찾을 수 없습니다: {url_file_path}")
        return []
    
    # URL 리스트 파일 이름에서 확장자를 제외한 이름으로 폴더 생성
    url_file_name = url_file_path.stem  # 확장자 제외한 파일명
    
    # 출력 디렉토리 설정 - 파일 이름과 동일한 폴더
    output_url_file_name = datetime.now().strftime("%Y%m%d_%H%M") + "_" + url_file_name
    output_dir = Path(__file__).parent.parent.parent / "data" / "crawling" / "jina_crawling" / output_url_file_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"크롤링 결과 저장 폴더: {output_dir}")
    
    # URL 목록 파일 읽기
    with open(url_file_path, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    logger.info(f"총 {len(urls)}개의 URL을 크롤링합니다. (최대 동시 작업자: {max_workers})")
    
    saved_files = []
    failed_urls = []
    
    # 진행 상황 표시를 위한 변수
    total_urls = len(urls)
    success_count = 0
    error_count = 0
    
    # ThreadPoolExecutor를 사용한 병렬 처리
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # URL을 작업으로 제출
        future_to_url = {
            executor.submit(process_single_url, url, output_dir, delay_range, verbose): url 
            for url in urls
        }
        
        # tqdm이 있으면 프로그레스 바 표시
        if TQDM_AVAILABLE:
            # 동적 출력을 위해 파라미터 설정
            pbar = tqdm(
                total=total_urls, 
                desc="URL 크롤링 중",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
            )
        
        # 결과 수집
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            
            try:
                success, result = future.result()
                
                if success:
                    saved_files.append(result)
                    success_count += 1
                    # 성공 시 상세 로그를 파일에만 기록
                    if verbose:
                        logger.debug(f"성공: {url} -> {result}")
                else:
                    failed_urls.append(url)
                    error_count += 1
                    # 실패 로그는 상세 모드에서만 출력
                    if verbose:
                        logger.warning(result)
                
                # 프로그레스바 업데이트
                if TQDM_AVAILABLE:
                    pbar.update(1)
                    # 진행률 표시에 성공/실패 정보 추가
                    pbar.set_postfix(성공=success_count, 실패=error_count)
                else:
                    # 10개 단위로 진행상황 출력
                    completed = success_count + error_count
                    if completed % 10 == 0 or completed == total_urls:
                        logger.info(f"진행 중: {completed}/{total_urls} (성공: {success_count}, 실패: {error_count})")
                
            except Exception as e:
                failed_urls.append(url)
                error_count += 1
                logger.error(f"작업 처리 예외 발생: {url}, 오류: {e}")
                # 프로그레스바 업데이트
                if TQDM_AVAILABLE:
                    pbar.update(1)
                    pbar.set_postfix(성공=success_count, 실패=error_count)
        
        if TQDM_AVAILABLE:
            pbar.close()
    
    # 최종 결과 요약
    logger.info(f"크롤링 완료: 성공 {success_count}, 실패 {error_count}, 총 {total_urls} URL 처리됨")
    
    if error_count > 0:
        logger.info(f"실패한 URL 수: {error_count}")
        # 실패한 URL 목록을 파일로 저장
        failed_file = output_dir / f"failed_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(failed_file, "w", encoding="utf-8") as f:
            for url in failed_urls:
                f.write(f"{url}\n")
        logger.info(f"실패한 URL 목록이 저장됨: {failed_file}")
    
    return saved_files


if __name__ == "__main__":
    # 시작 시간 기록
    start_time = datetime.now()
    logger.info(f"프로그램 실행 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # URL 리스트 파일에서 일괄 크롤링
    data_dir = Path(__file__).parent.parent.parent / "data" / "crawling"
    # url_list_file = data_dir / "20250511_0100_hansung_ac_kr_hansung" / "page_urls_20250511_0100.txt"
    url_list_file = data_dir / "20250510_1753_hansung_ac_kr_cse_cse" / "page_urls_20250510_1753.txt"
    
    # 병렬 처리로 크롤링 실행 (기본값: 최대 5개 스레드, 요청 간 0.5~1.5초 지연)
    # verbose=False로 설정하여 상세 로그를 출력하지 않음
    batch_jina_crawling(url_list_file, max_workers=5, delay_range=(0.5, 1.5), verbose=False)
    
    # 종료 시간 기록 및 실행 시간 계산
    end_time = datetime.now()
    execution_time = end_time - start_time
    
    logger.info(f"프로그램 실행 종료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"총 실행 시간: {execution_time}")