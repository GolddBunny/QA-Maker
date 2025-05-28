import requests
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime
import concurrent.futures
import random
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
from collections import deque

#TODO: 실패한 url list 다 끝나고, 다시 크롤링 해주는 로직 추가 필요
#TODO: 실패한 url list 파일 다른 곳에 저장

# artclView.do 또는 artclList.do가 제외된 URL만 필터링하여 크롤링해줌.
target_patterns = ['artclView.do', 'artclList.do', 'download.do', 'download.do?', '.pdf', '.pptx']

# 속도 조절을 위한 전역 변수
class ConservativeRateController:
    def __init__(self):
        self.current_delay = 1.5      # 시작 지연 시간
        self.min_delay = 1.0          # 최소 지연 시간
        self.max_delay = 20.0         # 최대 지연 시간
        self.success_count = 0        # 연속 성공 횟수
        self.error_count = 0          # 연속 에러 횟수
        self.recent_errors = deque(maxlen=20)  # 최근 20개 에러 추적
        self.recent_429_errors = deque(maxlen=10)  # 최근 429 에러만 추적
        self.lock = threading.Lock()
        self.last_429_time = 0        # 마지막 429 에러 시간
        
    def record_success(self):
        with self.lock:
            self.success_count += 1
            self.error_count = 0
            
            #연속 10회 성공 시에만 속도 증가
            if self.success_count >= 10:
                # 최근 1분 내 429 에러가 없을 때만 속도 증가
                recent_429 = any(err_time > time.time() - 60 for err_time in self.recent_429_errors)
                if not recent_429:
                    old_delay = self.current_delay
                    self.current_delay = max(self.min_delay, self.current_delay * 0.9)  # 10%만 감소
                    self.success_count = 0
                    if old_delay != self.current_delay:
                        logger.info(f"속도 소폭 증가: {old_delay:.2f}초 → {self.current_delay:.2f}초")
    
    def record_error(self, error_type):
        with self.lock:
            self.error_count += 1
            self.success_count = 0
            current_time = time.time()
            self.recent_errors.append(current_time)
            
            if "429" in str(error_type) or "rate limit" in str(error_type).lower():
                self.recent_429_errors.append(current_time)
                self.last_429_time = current_time
                
                # 429 에러 시 증가
                old_delay = self.current_delay
                self.current_delay = min(self.max_delay, self.current_delay * 1.5)  # 50% 증가
                logger.warning(f"Rate limit 감지: {old_delay:.2f}초 → {self.current_delay:.2f}초로 증가")
                
            elif self.error_count >= 5:
                # 일반 에러 연속 5회 시 소폭 증가
                old_delay = self.current_delay
                self.current_delay = min(self.max_delay, self.current_delay * 1.2)  # 20% 증가
                logger.warning(f"연속 에러 감지: {old_delay:.2f}초 → {self.current_delay:.2f}초로 증가")
    
    def get_delay(self):
        with self.lock:
            current_time = time.time()
            
            # 최근 429 에러가 있으면 추가 지연
            recent_429_count = sum(1 for err_time in self.recent_429_errors 
                                if err_time > current_time - 120)  # 2분 내
            
            base_delay = self.current_delay
            
            # 최근 429 에러가 많으면 추가 지연
            if recent_429_count >= 3:
                base_delay *= 1.5
            elif recent_429_count >= 1:
                base_delay *= 1.2
                
            # 최근 30초 내 429 에러가 있으면 더 큰 지연
            if self.last_429_time > current_time - 30:
                base_delay *= 2
                
            # 랜덤 지연 추가
            jitter = random.uniform(0, base_delay * 0.5)  # 0~50% 추가 지연
            
            return base_delay + jitter

# 전역 rate controller
rate_controller = ConservativeRateController()

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

# tqdm 조건부 임포트
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, **kwargs):
        total = len(iterable)
        for i, item in enumerate(iterable):
            if i % 50 == 0 or i + 1 == total:
                print(f"진행 중: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
            yield item

def create_session_with_retry():
    """재시도 로직이 포함된 requests 세션을 생성합니다."""
    session = requests.Session()
    
    # 재시도 전략
    retry_strategy = Retry(
        total=2,  
        status_forcelist=[500, 502, 503, 504],  # 429는 별도 처리
        backoff_factor=2,
        respect_retry_after_header=True
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def should_exclude_url(url):
    """URL이 제외 패턴에 해당하는지 확인합니다."""
    for pattern in target_patterns:
        if pattern in url:
            return True
    return False

def jina_crawling(crawl_url, output_dir, session=None, verbose=False):
    """단일 URL을 Jina를 통해 크롤링합니다."""
    if session is None:
        session = create_session_with_retry()
    
    if crawl_url.startswith(('http://', 'https://')):
        url = f"https://r.jina.ai/{crawl_url}"
    else:
        url = f"https://r.jina.ai/{crawl_url}"
    
    # Jina API 적용할 헤더
    headers = {
        "X-Md-Heading-Style": "setext",
        "X-Remove-Selector": ".class, #id, footer, a href",
        "X-Retain-Images": "none",
        "X-Cache-Tolerance": "7200",  # 2시간 캐시 활용
        "Accept": "text/plain",
    }
    
    # 적응형 지연 시간 적용
    delay = rate_controller.get_delay()
    if verbose:
        logger.debug(f"지연 시간: {delay:.2f}초 for {crawl_url}")
    time.sleep(delay)
    
    try:
        response = session.get(url, headers=headers, timeout=30)  # 타임아웃 복원
        response.raise_for_status()
        
        # 성공 기록
        rate_controller.record_success()
        
    except requests.exceptions.RequestException as e:
        # 에러 기록
        rate_controller.record_error(e)
        
        if "429" in str(e) or "rate limit" in str(e).lower():
            logger.warning(f"Rate limit 발생: {crawl_url}")
            # 429 에러 시 점진적 백오프로 재시도
            max_retries = 3
            for retry in range(max_retries):
                backoff_time = (2 ** retry) * random.uniform(3, 8)  # 3-8초, 6-16초, 12-32초
                logger.info(f"429 에러 재시도 {retry + 1}/{max_retries}: {backoff_time:.1f}초 대기")
                time.sleep(backoff_time)
                
                try:
                    response = session.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    logger.info(f"재시도 성공: {crawl_url}")
                    rate_controller.record_success()
                    break  # 성공하면 반복문 종료
                except requests.exceptions.RequestException as retry_e:
                    if retry == max_retries - 1:  # 마지막 재시도
                        logger.error(f"최종 재시도 실패: {crawl_url}")
                        raise retry_e
                    else:
                        logger.warning(f"재시도 {retry + 1} 실패, 계속 시도: {crawl_url}")
            else:
                # 모든 재시도 실패
                raise e
        else:
            raise e
    
    # 파일 저장 로직 (기존과 동일)
    parsed_url = urlparse(url)
    
    title = None
    try:
        title_match = re.search(r'Title:\s*(.*?)(?:\n|$)', response.text)
        if title_match:
            title = re.sub(r'[\\/*?:"<>|]', '', title_match.group(1).strip())[:50]
    except:
        pass
    
    if title:
        filename = f"{title}.txt"
    else:
        try:
            page_name = crawl_url.split('/')[-1].split('.')[0]
            filename = f"{page_name}.txt" if page_name else f"page_{hash(crawl_url) % 10000}.txt"
        except:
            filename = f"page_{hash(crawl_url) % 10000}.txt"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / filename
    counter = 1
    original_path = file_path
    while file_path.exists():
        stem = original_path.stem
        file_path = output_dir / f"{stem}_{counter}.txt"
        counter += 1
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    if verbose:
        logger.debug(f"저장: {file_path}")
    
    return str(file_path)

def process_single_url(url, output_dir, session, verbose=False):
    """단일 URL을 처리하는 함수."""
    try:
        file_path = jina_crawling(url, output_dir, session, verbose)
        return True, file_path
    except Exception as e:
        error_msg = f"URL 크롤링 실패: {url}, 오류: {e}"
        if verbose:
            logger.error(error_msg)
        return False, error_msg

def batch_jina_crawling(url_list_file, output_dir=None, max_workers=4, verbose=False):
    """URL 목록 파일에서 URL을 읽어 병렬 크롤링
    
    Args:
        url_list_file: URL 목록이 저장된 파일 경로
        output_dir: 결과를 저장할 디렉토리 경로
        max_workers: 동시에 실행할 최대 작업자 수 (기본값 4로 감소)
        verbose: 상세 로그 출력 여부
    """
    url_file_path = Path(url_list_file)
    
    if not url_file_path.exists():
        logger.error(f"URL 목록 파일을 찾을 수 없습니다: {url_file_path}")
        return []
    
    # 출력 디렉토리 설정
    if output_dir is not None:
        # 제공된 output_dir 그대로 사용
        output_dir = Path(output_dir)
    else:
        # 기본 경로 생성 (output_dir이 None인 경우에만)
        url_file_name = url_file_path.stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_dir = Path(__file__).parent.parent.parent / "data" / "qaSystem" / f"{timestamp}_{url_file_name}"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # URL 목록 읽기 및 필터링
    with open(url_file_path, 'r', encoding='utf-8') as f:
        all_urls = [line.strip() for line in f if line.strip()]
    
    urls = []
    excluded_urls = []
    
    for url in all_urls:
        if should_exclude_url(url):
            excluded_urls.append(url)
        else:
            urls.append(url)
    
    logger.info(f"전체 URL 수: {len(all_urls)}")
    logger.info(f"제외된 URL 수: {len(excluded_urls)}")
    logger.info(f"크롤링 대상 URL 수: {len(urls)}")
    
    # 제외된 URL 저장
    if excluded_urls:
        excluded_file = output_dir / f"excluded_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(excluded_file, "w", encoding="utf-8") as f:
            for url in excluded_urls:
                f.write(f"{url}\n")
        logger.info(f"제외된 URL 목록 저장: {excluded_file}")
    
    if not urls:
        logger.warning("크롤링할 URL이 없습니다.")
        return []
    
    saved_files = []
    failed_urls = []
    total_urls = len(urls)
    success_count = 0
    error_count = 0
    
    # 예상 시간 계산
    avg_delay = rate_controller.current_delay * 1.5  # 여유분 포함
    estimated_time = (total_urls * avg_delay) / max_workers / 60
    logger.info(f"총 {total_urls}개 URL 크롤링 시작 (동시 작업자: {max_workers})")
    logger.info(f"예상 완료 시간: 약 {estimated_time:.1f}분 (추정)")
    logger.info(f"시작 지연 시간: {rate_controller.current_delay:.2f}초")
    
    # 세션 풀 생성
    sessions = [create_session_with_retry() for _ in range(max_workers)]
    
    # 배치 크기 조정
    batch_size = 50 
    url_batches = [urls[i:i + batch_size] for i in range(0, len(urls), batch_size)]
    
    for batch_idx, url_batch in enumerate(url_batches):
        logger.info(f"배치 {batch_idx + 1}/{len(url_batches)} 처리 중 ({len(url_batch)}개 URL)")
        logger.info(f"현재 지연 시간: {rate_controller.current_delay:.2f}초")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {}
            for i, url in enumerate(url_batch):
                session = sessions[i % len(sessions)]
                future = executor.submit(process_single_url, url, output_dir, session, verbose)
                future_to_url[future] = url
            
            # 진행률 표시
            if TQDM_AVAILABLE:
                pbar = tqdm(
                    total=len(url_batch), 
                    desc=f"배치 {batch_idx + 1}",
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
                )
            
            # 결과 수집
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                
                try:
                    success, result = future.result()
                    
                    if success:
                        saved_files.append(result)
                        success_count += 1
                    else:
                        failed_urls.append(url)
                        error_count += 1
                    
                    if TQDM_AVAILABLE:
                        pbar.update(1)
                        pbar.set_postfix(
                            성공=success_count, 
                            실패=error_count,
                            지연=f"{rate_controller.current_delay:.1f}s"
                        )
                    
                except Exception as e:
                    failed_urls.append(url)
                    error_count += 1
                    if verbose:
                        logger.error(f"작업 예외: {url}, 오류: {e}")
                    
                    if TQDM_AVAILABLE:
                        pbar.update(1)
                        pbar.set_postfix(성공=success_count, 실패=error_count)
            
            if TQDM_AVAILABLE:
                pbar.close()
        
        # 배치 간 휴식 시간 증가
        if batch_idx < len(url_batches) - 1:
            batch_rest = 2 + (rate_controller.error_count * 0.5)  # 에러가 많을수록 더 긴 휴식
            logger.info(f"배치 간 휴식: {batch_rest:.1f}초")
            time.sleep(batch_rest)
    
    # 세션 정리
    for session in sessions:
        session.close()
    
    # 최종 결과
    success_rate = (success_count / total_urls) * 100 if total_urls > 0 else 0
    logger.info(f"크롤링 완료: 성공 {success_count}, 실패 {error_count}, 성공률 {success_rate:.1f}%")
    logger.info(f"최종 지연 시간: {rate_controller.current_delay:.2f}초")
    
    if failed_urls:
        failed_file = output_dir / f"failed_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(failed_file, "w", encoding="utf-8") as f:
            for url in failed_urls:
                f.write(f"{url}\n")
        logger.info(f"실패한 URL 목록 저장: {failed_file}")
    
    return saved_files


if __name__ == "__main__":
    start_time = datetime.now()
    logger.info(f"프로그램 실행 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # URL 리스트 파일 경로
    data_dir = Path(__file__).parent.parent.parent / "data" / "crawling"
    url_list_file = data_dir / "20250526_0412_hansung_ac_kr_sites_hansung" / "page_urls_20250526_0412.txt"
    
    # 병렬 크롤링 실행 (동시 작업자 감소, 안정성 우선)
    batch_jina_crawling(url_list_file, max_workers=4, verbose=False)
    
    end_time = datetime.now()
    execution_time = end_time - start_time
    
    logger.info(f"프로그램 실행 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"총 실행 시간: {execution_time}")
    logger.info(f"최종 평균 지연 시간: {rate_controller.current_delay:.2f}초")