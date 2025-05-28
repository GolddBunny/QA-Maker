from bs4 import BeautifulSoup   # html 파싱 + 데이터 추출 : find_all(조건에 맞는 모든 태그 찾기), select(css 선택자 사용)
import os                       # 파일 시스템 사용
import time                     
import random                   
import re                       # 정규 표현식 처리 : sub(문자열 치환)
import json                     
import logging                  
import base64                   # base64 인코딩/디코딩 처리
from urllib.parse import urlparse, urljoin, parse_qs    # url 파싱 + 분석/조합/쿼리파라미터처리 : urlparse(url 분석), urljoin(url 조합), parse_qs(쿼리 파라미터 추출)
from datetime import datetime
from typing import Set, List, Dict, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed       # 비동기 작업 처리 : ThreadPoolExecutor(스레드 풀 관리). 병렬 작업 처리
import requests                                         # 정적 웹페이지 크롤링: 웹 요청 처리(get, post) + 웹 페이지 다운로드(text, json)
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError
from selenium import webdriver                          # 동적 웹페이지 크롤링: 웹 브라우저 자동화(자바스크립트 실행). WebDriverWait(특정 요소가 나타날 때까지 대기)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSelectorException
from webdriver_manager.chrome import ChromeDriverManager
import threading                                        # 스레드 안전성을 위한 락
import heapq                                            # 우선순위 큐 구현
from collections import OrderedDict                     # LRU 캐시 구현용
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crawler.log")
    ]
)
logger = logging.getLogger("scope_crawler")

# 상수 정의
#BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "crawling")
BASE_DIR = Path(__file__).parent / "urlCrawling_CSE"

# 유저 에이전트 정의
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    
]
# 문서 파일 확장자 패턴
DOC_EXTENSIONS = ['.pdf', '.docx', '.doc', '.hwp', '.txt', '.hwpx', 'word']

# 제외할 url 패턴
EXCLUDE_PATTERNS = [
    '/login', '/logout', '/search?', 'javascript:', '#', 'mailto:', 'tel:',
    '/api/', '/rss/', 'comment', 'print.do', 'popup', 'redirect', 'captcha', 'admin', 
    'synapview.do?', '/synapview.do?', '/synap', '/synap/view.do', '/synap/view.do?', 
    'artclpasswordchckview.do', 'schdulexcel.do', '.php',
    '/hansung/8390', 'book.hansung.ac.kr/review-type/', 'https://book.hansung.ac.kr/', 'https://cms.hansung.ac.kr/em/'
]

# 게시판 목록 페이지 패턴 (URL 목록에서 제외하되 링크는 추출)
LIST_PAGE_PATTERNS = [
    'artcllist.do', 'rsslist.do'
]

# 제외할 파일 확장자
EXCLUDE_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.tif', '.tiff', '.ico', '.webp', 
    '.html', '.htm', '.css', '.js', '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', 
    '.mkv', '.tmp', '.zip', '.xls', '.xlsx', '.wma', '.wav', '.rar', '.7z'  # xls, wma 등 추가
]

# 페이지네이션 감지를 위한 CSS 식별자
PAGINATION_SELECTORS = [
    ".pagination", "nav.pagination", "ul.pagination", ".paging", "._paging", "_totPage"
    ".page-navigation", ".paginate", "ul.page-numbers", ".pagenavigation", ".page-nav",
    "[class*='paging']", "[class*='pagination']", "[class*='page_navi']", ".board_paging",
    ".paginator", ".navigator", ".list_page", "#paging", "#pagination", ".page-list",
    ".board-paging", ".pager", ".pages", ".page-selector", ".pagenate"
]

# 페이지 번호 링크 감지를 위한 XPath 패턴: XML 문서의 요소와 속성을 탐색하기 위한 쿼리 언어
PAGE_NUMBER_PATTERNS = [
    "//a[contains(@href, 'page=')]", "//a[contains(@href, 'pageIndex=')]", 
    "//a[contains(@href, 'pageNo=')]", "//a[contains(@class, 'page-link')]",
    "//a[contains(@class, 'page-')]", "//a[contains(text(), '다음')]",
    "//a[contains(@class, 'next')]", "//a[contains(text(), '다음 페이지')]",
    "//a[contains(text(), '다음 페이지')]", "//a[contains(text(), 'Next')]"
]

# 첨부파일 클래스 식별자
ATTACHMENT_CLASSES = [
    'attachment', 'attachments', 'file-download', 'download-file', 
    'document-link', 'file-list', 'view-file', 'board-file',
    'filearea', 'file-area', 'download-area', 'download-box', 'download'
]

# 다운로드 URL 패턴
DOWNLOAD_PATTERNS = [
    '/download', '/file', '/attach', 'fileDown', 'getFile', 
    'downloadFile', 'downFile', 'fileview', 'download', 'download.do', 'fileDown.do', 'download.do', 'downloadFile.do'
]

# 다양한 오류 메시지 패턴 확인
ERROR_PATTERNS = [
    'alert 404', 'alert 500', 'alert 403', 'alert 400', 'error', '404', '500', '403', 'alert',
    '관리모드 > 알림메세지', '관리모드'
]

# URL 우선순위 정의
class URLPriority:
    HIGH = 1      # 사이트맵, 메인 페이지
    NORMAL = 2    # 일반 페이지
    LOW = 3       # 페이지네이션

class LRUCache:
    """스레드 안전한 LRU 캐시 구현"""
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[str]:
        with self.lock:
            if key in self.cache:
                # 최근 사용으로 이동
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def put(self, key: str, value: str) -> None:
        with self.lock:
            if key in self.cache:
                # 기존 값 업데이트
                self.cache.move_to_end(key)
            else:
                # 새 값 추가
                if len(self.cache) >= self.max_size:
                    # 가장 오래된 항목 제거
                    self.cache.popitem(last=False)
            self.cache[key] = value
    
    def clear(self) -> None:
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        with self.lock:
            return len(self.cache)

class ScopeLimitedCrawler:
    def __init__(self, max_pages: int = 100000, delay: float = 1.0, timeout: int = 20, use_requests: bool = True):
        """크롤러 초기화.
        
        Args:
            max_pages: 크롤링할 최대 페이지 수
            delay: 요청 간 지연 시간(초)
            timeout: 페이지 로딩 시간 제한(초)
            use_requests: 간단한 페이지는 requests 사용, JS가 많은 페이지는 selenium 사용
        """
        # 통합된 스레드 안전성을 위한 RLock 사용
        self.url_lock = threading.RLock()
        
        # URL 관리를 위한 자료구조 (스레드 안전)
        self.visited_urls: Set[str] = set()  # 방문한 URL 집합
        self.excluded_urls: Set[str] = set()  # 제외된 URL 집합
        self.queued_urls: Set[str] = set()   # 큐에 추가된 URL 집합 (중복 방지)
        self.all_page_urls: Set[str] = set() # 모든 페이지 URL
        self.all_doc_urls: Set[str] = set()  # 모든 문서 URL
        
        # URL 정규화 캐시
        self.normalization_cache = LRUCache(max_size=50000)
        
        self.base_domain: str = ""  # 기본 도메인
        self.scope_patterns: List[str] = []  # 크롤링 범위 패턴
        self.max_pages: int = max_pages  # 최대 페이지 수
        self.delay: float = delay  # 요청 간 지연 시간
        self.timeout: int = timeout  # 페이지 로딩 시간 제한
        self.use_requests: bool = use_requests  # requests 라이브러리 사용 여부
        self.session = requests.Session()  # 세션 생성
        self.session.headers.update({"User-Agent": random.choice(USER_AGENTS)})  # 랜덤 User-Agent 설정
        
        # Selenium 드라이버 접근을 위한 스레드 락 추가
        self.driver_lock = threading.Lock()

        # 결과 저장 디렉토리
        os.makedirs(BASE_DIR, exist_ok=True)
        
        # Selenium 초기화 (필요할 때만)
        self.driver = None

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 시 리소스 정리"""
        self.cleanup()

    def cleanup(self):
        """모든 리소스 정리"""
        self.close_driver()
        if hasattr(self, 'session') and self.session:
            self.session.close()
            logger.info("HTTP 세션이 정리되었습니다")
        
        # 캐시 정리
        if hasattr(self, 'normalization_cache'):
            self.normalization_cache.clear()
            logger.info("정규화 캐시가 정리되었습니다")

    def _init_selenium(self) -> None:
        """Selenium WebDriver를 초기화 (스레드 안전)"""
        with self.driver_lock:
            if self.driver is not None:
                # 기존 드라이버가 응답하는지 확인
                try:
                    self.driver.current_url  # 상태 확인
                    return  # 정상 작동 중이면 재사용
                except:
                    # 응답하지 않으면 재생성
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                    
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--blink-settings=imagesEnabled=false')
            chrome_options.add_argument('--disk-cache-size=52428800')
            
            # JavaScript 오류 무시 옵션 추가
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            
            # 성능 최적화 설정 - 이미지, 알림, 스타일시트, 쿠키, 자바스크립트, 플러그인, 팝업, 지리정보, 미디어스트림. 1은 허용, 2는 비허용
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
                "profile.managed_default_content_settings.cookies": 1,
                "profile.managed_default_content_settings.javascript": 1,
                "profile.managed_default_content_settings.plugins": 1,
                "profile.managed_default_content_settings.popups": 2,
                "profile.managed_default_content_settings.geolocation": 2,
                "profile.managed_default_content_settings.media_stream": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            try:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(self.timeout)
            except Exception as e:
                logger.error(f"Selenium 드라이버 초기화 실패: {e}")
                # 실패 시 재시도
                try:
                    time.sleep(1)
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.driver.set_page_load_timeout(self.timeout)
                except Exception as e:
                    logger.error(f"Selenium 드라이버 재초기화 실패: {e}")
                    raise

    def __del__(self) -> None:
        """객체가 소멸될 때 리소스 정리 (백업용)"""
        try:
            # cleanup이 이미 호출되었는지 확인
            if hasattr(self, 'driver') and self.driver is not None:
                logger.warning("__del__에서 리소스 정리 - cleanup()이 명시적으로 호출되지 않았습니다")
                self.cleanup()
        except Exception as e:
            # __del__에서는 예외를 발생시키지 않음
            pass

    def close_driver(self) -> None:
        """Selenium 드라이버 안전하게 종료"""
        if hasattr(self, 'driver') and self.driver is not None:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("웹드라이버가 성공적으로 종료되었습니다")
            except Exception as e:
                logger.error(f"웹드라이버 종료 중 오류 발생: {e}")

    def check_page_title(self, html_content: str) -> bool:
        """페이지 head 영역에서 오류 메시지 확인 (Alert 404, Alert 500, 관리모드 등)"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. 페이지 제목 확인
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                title_text = title_tag.string.strip().lower()
                
                for pattern in ERROR_PATTERNS:
                    if pattern.lower() in title_text:
                        logger.warning(f"오류 페이지 제목 감지 (패턴: '{pattern}'): {title_text}")
                        return True
            
            # 2. head 영역의 meta 태그 확인
            head_tag = soup.find('head')
            if head_tag:
                # meta description, keywords 등 확인
                meta_tags = head_tag.find_all('meta')
                for meta in meta_tags:
                    content = meta.get('content', '').lower()
                    name = meta.get('name', '').lower()
                    
                    for pattern in ERROR_PATTERNS:
                        if pattern.lower() in content or pattern.lower() in name:
                            logger.warning(f"오류 페이지 meta 태그 감지 (패턴: '{pattern}')")
                            return True
            
            # 3. 특정 오류 관련 클래스나 ID 확인 (head 영역만)
            error_selectors = [
                'head .error', 'head #error', 'head .alert-error', 'head .error-message', 
                'head .not-found', 'head .page-not-found', 'head .admin-mode', 'head .관리모드'
            ]
            
            for selector in error_selectors:
                try:
                    error_elements = soup.select(selector)
                    if error_elements:
                        logger.warning(f"오류 페이지 요소 감지 (선택자: '{selector}')")
                        return True
                except Exception as selector_error:
                    # CSS 선택자 오류는 무시하고 계속 진행
                    logger.debug(f"CSS 선택자 오류 무시: {selector} - {selector_error}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"페이지 head 영역 확인 중 오류 발생: {e}")
            return False

    def normalize_url(self, url: str) -> str:
        """URL 정규화하여 프래그먼트와 후행 슬래시 제거, 페이지네이션 고려 (캐시 적용)"""
        if not url:
            return ""
        
        # 캐시에서 확인
        cached_result = self.normalization_cache.get(url)
        if cached_result is not None:
            return cached_result
        
        original_url = url
        
        # 프래그먼트 제거
        if '#' in url:
            url = url.split('#')[0]
        
        # 프로토콜 확인
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url
        
        # URL 파싱
        parsed = urlparse(url)
        path = parsed.path
        query_params = parse_qs(parsed.query)
        
        # 파일 확장자 확인하여 제외
        if any(path.lower().endswith(ext) for ext in EXCLUDE_EXTENSIONS):
            self.normalization_cache.put(original_url, "")
            return ""
        
        # 기본 URL (경로까지)
        base_url = f"{parsed.scheme}://{parsed.netloc}{path}"
        
        # 도메인 루트인 경우 그대로 반환
        if parsed.path == '/':
            self.normalization_cache.put(original_url, url)
            return url
        
        # http와 https 표준화 (https 사용)
        if parsed.scheme == 'http':
            base_url = base_url.replace('http://', 'https://')
        
        # www와 non-www 표준화 (동일한 사이트로 처리)
        if parsed.netloc.startswith('www.'):
            non_www = base_url.replace(f"{parsed.scheme}://www.", f"{parsed.scheme}://")
            base_url = non_www
        else:
            www_version = base_url.replace(f"{parsed.scheme}://", f"{parsed.scheme}://www.")
            if self.base_domain.startswith('www.') and not parsed.netloc.startswith('www.'):
                base_url = www_version
        
        # 쿼리 파라미터 정규화
        normalized_query_params = {}
        
        # 직접적인 페이지 파라미터가 있는 경우
        if 'page' in query_params:
            page_num = query_params['page'][0]
            # page=1인 경우 쿼리 파라미터 제거 (기본 URL만 반환)
            if page_num == '1':
                result = base_url
            else:
                result = f"{base_url}?page={page_num}"
            self.normalization_cache.put(original_url, result)
            return result
        
        # enc 파라미터에서 페이지 번호 추출 시도
        if 'enc' in query_params:
            enc_value = query_params['enc'][0]
            try:
                # Base64 디코딩 시도
                decoded = base64.b64decode(enc_value).decode('utf-8')
                
                # 페이지 번호 추출을 위한 정규식
                page_match = re.search(r'page%3D(\d+)', decoded)
                if page_match:
                    page_num = page_match.group(1)
                    # page=1인 경우 쿼리 파라미터 제거 (기본 URL만 반환)
                    if page_num == '1':
                        result = base_url
                    else:
                        result = f"{base_url}?page={page_num}"
                    self.normalization_cache.put(original_url, result)
                    return result
            except Exception as e:
                logger.debug(f"Base64 디코딩 실패: {e}")
                # 디코딩 실패 시 계속 진행
                pass
        
        # 다른 일반적인 페이지네이션 파라미터 확인
        for page_param in ['pageNo', 'pageIndex', 'p', 'pg', 'pageNum']:
            if page_param in query_params:
                page_num = query_params[page_param][0]
                # page 번호가 1인 경우 쿼리 파라미터 제거 (기본 URL만 반환)
                if page_num == '1':
                    result = base_url
                else:
                    result = f"{base_url}?page={page_num}"  # 표준화된 형식으로 변환
                self.normalization_cache.put(original_url, result)
                return result
        
        # 중요한 쿼리 파라미터 보존 (검색, 카테고리 등)
        important_params = ['q', 'query', 'search', 'category', 'type', 'id', 'no']
        for param in important_params:
            if param in query_params:
                normalized_query_params[param] = query_params[param][0]
        
        # 정규화된 쿼리 문자열 생성
        if normalized_query_params:
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(normalized_query_params.items())])
            result = f"{base_url}?{query_string}"
        else:
            # 쿼리 파라미터가 없는 URL의 후행 슬래시 제거
            result = base_url.rstrip('/')
        
        # 캐시에 저장
        self.normalization_cache.put(original_url, result)
        return result

    def is_in_scope(self, url: str) -> bool:
        """URL이 정의된 크롤링 범위 내에 있는지 확인 (스레드 안전)"""
        try:
            parsed = urlparse(url)
            
            # 도메인 확인 - 기본 도메인에 속해야 함
            if self.base_domain not in parsed.netloc:
                return False
            
            # scope_patterns가 비어있거나 빈 문자열만 있으면 도메인 전체 허용
            if not self.scope_patterns or (len(self.scope_patterns) == 1 and self.scope_patterns[0] == ''):
                return True
            
            # URL 경로를 소문자로 변환하여 패턴 매칭
            url_path = parsed.path.lower()
            url_query = parsed.query.lower()
            full_url_lower = url.lower()
            
            # scope_patterns가 2개 이상인 경우 모든 패턴이 포함되어야 함
            if len(self.scope_patterns) >= 2:
                matched_patterns = []
                for pattern in self.scope_patterns:
                    pattern_lower = pattern.lower()
                    
                    # 패턴이 경로, 쿼리, 또는 전체 URL에 포함되는지 확인
                    if (pattern_lower in url_path or 
                        pattern_lower in url_query or 
                        pattern_lower in full_url_lower):
                        matched_patterns.append(pattern)
                
                # 모든 패턴이 매칭되어야 범위 내로 판단
                if len(matched_patterns) == len(self.scope_patterns):
                    logger.debug(f"URL이 범위 내에 있음 (모든 패턴 매칭): {url} (패턴: {self.scope_patterns}, 매칭된 패턴: {matched_patterns})")
                    return True
                else:
                    logger.debug(f"URL이 범위 밖 (일부 패턴만 매칭): {url} (패턴: {self.scope_patterns}, 매칭된 패턴: {matched_patterns})")
                    return False
            else:
                # scope_patterns가 1개인 경우 기존 로직 유지 (하나라도 매칭되면 허용)
                for pattern in self.scope_patterns:
                    pattern_lower = pattern.lower()
                    
                    # 패턴이 경로, 쿼리, 또는 전체 URL에 포함되는지 확인
                    if (pattern_lower in url_path or 
                        pattern_lower in url_query or 
                        pattern_lower in full_url_lower):
                        logger.debug(f"URL이 범위 내에 있음: {url} (패턴: {pattern})")
                        return True
                
                # 어떤 패턴도 매칭되지 않으면 범위 밖
                logger.debug(f"URL이 범위 밖: {url} (패턴: {self.scope_patterns})")
                return False
            
        except Exception as e:
            logger.error(f"URL 범위 확인 중 오류 발생: {e}")
            return False
    
    def should_exclude_url(self, url: str) -> bool:
        """URL이 정의된 패턴에 따라 제외되어야 하는지 확인 (스레드 안전)"""
        with self.url_lock:
            # 이미 제외로 확인된 URL인지 검사
            if url in self.excluded_urls:
                return True
                
            lower_url = url.lower()
            
            # 제외 패턴 확인
            for pattern in EXCLUDE_PATTERNS:
                if pattern in lower_url:
                    logger.info(f"제외 패턴 '{pattern}' 매칭으로 URL 제외: {url}")
                    self.excluded_urls.add(url)  # 제외 URL 목록에 추가
                    return True
                    
            return False

    def is_list_page(self, url: str) -> bool:
        """URL이 게시판 목록 페이지인지 확인"""
        lower_url = url.lower()
        for pattern in LIST_PAGE_PATTERNS:
            if pattern in lower_url:
                return True
        return False

    def is_valid_file_url(self, href: str, base_url: str) -> bool:
        """URL이 유효한 문서 파일 URL인지 확인 (DOC_EXTENSIONS + 특정 다운로드 패턴)"""
        if not href or href == '#' or href.startswith(('javascript:', 'mailto:', 'tel:')):
            return False
        
        lower_url = href.lower()
        
        # 제외할 확장자 확인
        if any(lower_url.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
            return False
        
        # 제외 패턴 확인
        for pattern in EXCLUDE_PATTERNS:
            if pattern in lower_url:
                return False
        
        # 1. 문서 파일 확장자 확인 (DOC_EXTENSIONS에 해당하는 것만)
        for ext in DOC_EXTENSIONS:
            if lower_url.endswith(ext):
                return True
        
        # 2. 명확한 문서 다운로드 패턴 확인 (게시판의 첨부파일 다운로드 등)
        for pattern in DOWNLOAD_PATTERNS:
            if pattern in lower_url:
                # 명확히 제외해야 할 패턴들 확인
                exclude_keywords = ['software', 'program', 'app', 'installer', 'setup']
                if not any(keyword in lower_url for keyword in exclude_keywords):
                    # download.do와 fileDown.do는 항상 문서로 분류
                    if pattern in ['/download.do', 'download.do', 'fileDown.do']:
                        return True
                    # 기타 패턴은 게시판이나 첨부파일 관련 경로인지 확인
                    elif (any(keyword in lower_url for keyword in ['/bbs/', '/board/', '/attach', '/file', '/document']) or
                        not any(keyword in lower_url for keyword in ['software', 'media', 'image', 'video'])):
                        return True
        
        return False

    def add_url_atomically(self, url: str, url_set: Set[str]) -> bool:
        """URL을 원자적으로 집합에 추가 (중복 체크 포함)"""
        with self.url_lock:
            if url not in url_set:
                url_set.add(url)
                return True
            return False

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> Tuple[Set[str], Set[str]]:
        """페이지에서 일반 링크와 문서 링크 추출 (개선된 중복 처리)"""
        links = set()
        doc_links = set()
        
        try:
            # 1. 일반 링크 추출
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                
                # 빈 링크, 자바스크립트, 특수 프로토콜, 미디어 파일 등 건너뛰기
                if (not href or 
                    href.startswith(('javascript:', 'mailto:', 'tel:')) or 
                    href == '#' or
                    href.startswith('#')):  # 페이지 내 앵커 링크
                    continue
                
                # 절대 URL 생성 - 상대 경로 처리 개선
                if href.startswith('/'):
                    full_url = f"https://{self.base_domain}{href}"
                else:
                    full_url = urljoin(base_url, href)
                
                # URL 정규화 (캐시 적용)
                normalized_url = self.normalize_url(full_url)
                if not normalized_url:  # 정규화 실패 시 건너뛰기
                    continue
                
                # 제외 패턴 확인 (정규화된 URL로)
                if self.should_exclude_url(normalized_url):
                    continue
                
                # 문서 파일인지 확인 (DOC_EXTENSIONS 확장자만)
                is_doc = False
                lower_url = normalized_url.lower()

                # 1. 확장자 기반 문서 파일 확인
                for ext in DOC_EXTENSIONS:
                    if lower_url.endswith(ext):
                        doc_links.add(normalized_url)
                        is_doc = True
                        break
                
                # 2. 선별적 다운로드 패턴 확인 (게시판 첨부파일 등)
                if not is_doc:
                    for pattern in DOWNLOAD_PATTERNS:
                        if pattern in lower_url:
                            # 명확히 제외해야 할 패턴들 확인
                            exclude_keywords = ['software', 'program', 'app', 'installer', 'setup']
                            if not any(keyword in lower_url for keyword in exclude_keywords):
                                # download.do와 fileDown.do는 항상 문서로 분류
                                if pattern in ['/download.do', 'download.do', 'fileDown.do']:
                                    doc_links.add(normalized_url)
                                    is_doc = True
                                    break
                                # 기타 패턴은 게시판이나 첨부파일 관련 경로인지 확인
                                elif (any(keyword in lower_url for keyword in ['/bbs/', '/board/', '/attach', '/file', '/document']) or
                                    not any(keyword in lower_url for keyword in ['software', 'media', 'image', 'video'])):
                                    doc_links.add(normalized_url)
                                    is_doc = True
                                    break
                
                # 일반 URL 추가 (범위 확인)
                if not is_doc and self.is_in_scope(normalized_url):
                    links.add(normalized_url)
                elif not is_doc:
                    # 범위 밖 URL 로깅 (디버그 레벨)
                    logger.debug(f"범위 밖 URL 제외: {normalized_url}")
                    
            # 2. 메뉴 및 네비게이션 링크 특별 처리
            nav_selectors = [
                'nav a', '.nav a', '.navigation a', '.menu a', '.gnb a', '.lnb a',
                '.main-menu a', '.sub-menu a', '.sidebar a', '.footer a',
                '[class*="menu"] a', '[class*="nav"] a', '[id*="menu"] a', '[id*="nav"] a'
            ]
            
            for selector in nav_selectors:
                nav_links = soup.select(selector)
                for link in nav_links:
                    if link.has_attr('href'):
                        href = link['href']
                        if href and href != '#' and not href.startswith(('javascript:', 'mailto:', 'tel:')):
                            if href.startswith('/'):
                                full_url = f"https://{self.base_domain}{href}"
                            else:
                                full_url = urljoin(base_url, href)
                            
                            normalized_url = self.normalize_url(full_url)
                            if (normalized_url and 
                                not self.should_exclude_url(normalized_url) and 
                                self.is_in_scope(normalized_url)):
                                links.add(normalized_url)
                            elif normalized_url:
                                # 범위 밖 네비게이션 링크 로깅
                                logger.debug(f"범위 밖 네비게이션 링크 제외: {normalized_url}")

            # 3. 첨부파일 추출
            attachment_links = self.extract_attachments(soup, base_url)
            doc_links.update(attachment_links)
            
            # 디버깅 로그 추가
            logger.debug(f"링크 추출 완료 - 일반: {len(links)}개, 문서: {len(doc_links)}개")
                    
            return links, doc_links
            
        except Exception as e:
            logger.error(f"링크 추출 중 오류 발생: {e}")
            return set(), set()

    def extract_attachments(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """페이지에서 첨부파일 링크 추출"""
        doc_links = set()
        
        try:
            # 1. 첨부파일 클래스 확인 (ATTACHMENT_CLASSES 상수 활용)
            for class_name in ATTACHMENT_CLASSES:
                # 클래스명이 포함된 모든 요소 찾기
                sections = soup.find_all(class_=lambda c: c and class_name in str(c).lower())
                for section in sections:
                    links = section.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        # synapview.do 링크 제외
                        if 'synapView.do' in href.lower():
                            continue

                        if self.is_valid_file_url(href, base_url):
                            if href.startswith('/'):
                                full_url = f"https://{self.base_domain}{href}"
                            else:
                                full_url = urljoin(base_url, href)
                            
                            # 문서 URL도 정규화하여 추가
                            normalized_url = self.normalize_url(full_url)
                            if normalized_url:
                                doc_links.add(normalized_url)
            
            # 2. 파일 관련 속성 확인 (ATTACHMENT_CLASSES 기반)
            file_keywords = ['file', 'attach', 'download'] + ATTACHMENT_CLASSES
            file_related_elements = soup.find_all(
                ['a', 'span', 'div', 'li'], 
                attrs=lambda attr: attr and any(
                    keyword in str(attr).lower() 
                    for keyword in file_keywords
                )
            )
            
            for element in file_related_elements:
                links = [element] if element.name == 'a' and element.has_attr('href') else element.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if self.is_valid_file_url(href, base_url):
                        if href.startswith('/'):
                            full_url = f"https://{self.base_domain}{href}"
                        else:
                            full_url = urljoin(base_url, href)
                            
                        # 문서 URL도 정규화하여 추가
                        normalized_url = self.normalize_url(full_url)
                        if normalized_url:
                            doc_links.add(normalized_url)
            
            # 3. DOWNLOAD_PATTERNS를 포함하는 모든 링크 직접 검색
            for link in soup.find_all('a', href=True):
                href = link['href']
                lower_href = href.lower()
                
                # DOWNLOAD_PATTERNS 중 하나라도 포함되면 검사
                if any(pattern in lower_href for pattern in DOWNLOAD_PATTERNS):
                    if self.is_valid_file_url(href, base_url):
                        if href.startswith('/'):
                            full_url = f"https://{self.base_domain}{href}"
                        else:
                            full_url = urljoin(base_url, href)
                            
                        # 문서 URL도 정규화하여 추가
                        normalized_url = self.normalize_url(full_url)
                        if normalized_url:
                            doc_links.add(normalized_url)
                            
            return doc_links
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류 발생: {e}")
            return set()

    def fetch_page(self, url: str, max_retries: int = 1) -> Tuple[bool, Any, str]:
        """설정에 따라 requests 또는 selenium을 사용하여 페이지 내용을 가져옴."""
        url = self.normalize_url(url)
        
        # JavaScript:로 시작하는 URL 처리
        if url.startswith('javascript:'):
            logger.debug(f"JavaScript URL 감지: {url}")
            return False, None, url
        
        # 재시도 횟수 설정
        retries = 0
        
        while retries <= max_retries:
            try:
                # 먼저 requests 사용 시도 (활성화된 경우)
                if self.use_requests:
                    try:
                        # User-Agent 랜덤화 (캐싱 우회 및 차단 방지)
                        if retries > 0:
                            self.session.headers.update({"User-Agent": random.choice(USER_AGENTS)})
                            
                        response = self.session.get(url, timeout=self.timeout)
                        
                        # 여기가 수정된 부분 - raise_for_status() 호출 전에 500 에러 확인
                        if 500 <= response.status_code < 600:  # 모든 5xx 에러 처리
                            logger.warning(f"서버 오류 감지, 건너뜁니다: {url}, 상태 코드: {response.status_code}")
                            return False, None, url
                            
                        response.raise_for_status()
                        
                        # 자바스크립트가 많은 페이지인지 확인
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 페이지 제목이 오류 메시지인지 확인
                        if self.check_page_title(response.text):
                            logger.warning(f"오류 페이지 제목 감지, 건너뜁니다: {url}")
                            return False, None, url
                        
                        # 페이지가 자바스크립트를 필요로 하는 것 같으면 Selenium으로 전환
                        noscript_content = soup.find('noscript')
                        js_required = noscript_content and len(noscript_content.text) > 100
                        
                        if not js_required:
                            return True, soup, response.url
                            
                    except Timeout:
                        logger.warning(f"요청 타임아웃({retries+1}/{max_retries+1}): {url}")
                        retries += 1
                        if retries <= max_retries:
                            time.sleep(self.delay * retries)
                            continue
                        else:
                            logger.error(f"최대 재시도 횟수 초과 (타임아웃): {url}")
                            return False, None, url
                            
                    except ConnectionError:
                        logger.warning(f"연결 오류({retries+1}/{max_retries+1}): {url}")
                        retries += 1
                        if retries <= max_retries:
                            time.sleep(self.delay * retries * 2)  # 연결 오류 시 더 긴 대기
                            continue
                        else:
                            logger.error(f"최대 재시도 횟수 초과 (연결 오류): {url}")
                            return False, None, url
                            
                    except HTTPError as e:
                        if e.response.status_code in [404, 403, 401]:
                            logger.warning(f"HTTP 오류 {e.response.status_code}: {url}")
                            return False, None, url
                        else:
                            logger.warning(f"HTTP 오류({retries+1}/{max_retries+1}): {url}, 상태: {e.response.status_code}")
                            retries += 1
                            if retries <= max_retries:
                                time.sleep(self.delay * retries)
                                continue
                            else:
                                logger.error(f"최대 재시도 횟수 초과 (HTTP 오류): {url}")
                                return False, None, url
                                
                    except RequestException as e:
                        logger.warning(f"요청 오류({retries+1}/{max_retries+1}): {url}, 오류: {e}")
                        retries += 1
                        if retries <= max_retries:
                            time.sleep(self.delay * retries)
                            continue
                        else:
                            logger.error(f"최대 재시도 횟수 초과 (요청 오류): {url}")
                            return False, None, url
                
                # requests가 실패하거나 자바스크립트가 필요한 경우 Selenium 사용    
                try:
                    self._init_selenium()
                    
                    # 최대 2번 재시도 
                    for attempt in range(2):
                        try:
                            self.driver.get(url)
                            
                            # 로딩 후 페이지의 상태를 확인
                            if "500 error" in self.driver.page_source.lower() or "500 에러" in self.driver.page_source.lower():
                                logger.warning(f"500 에러 페이지 감지(Selenium), 건너뜁니다: {url}")
                                return False, None, url
                            
                            # 페이지 로드 대기
                            WebDriverWait(self.driver, self.timeout).until(
                                EC.presence_of_element_located((By.TAG_NAME, 'body'))
                            )
                            
                            html_content = self.driver.page_source
                            current_url = self.driver.current_url
                            
                            # 페이지 제목이 오류 메시지인지 확인
                            if self.check_page_title(html_content):
                                logger.warning(f"오류 페이지 제목 감지, 건너뜁니다: {url}")
                                return False, None, url
                            
                            soup = BeautifulSoup(html_content, 'html.parser')
                            return True, soup, current_url
                            
                        except TimeoutException:
                            if attempt < 1:  # 첫 번째 시도가 실패한 경우에만 재시도
                                logger.warning(f"페이지 로딩 타임아웃, 재시도 중: {url}")
                                continue
                            raise
                            
                except Exception as e:
                    logger.warning(f"Selenium 처리 오류({retries+1}/{max_retries+1}): {url}, 오류: {e}")
                    retries += 1
                    if retries <= max_retries:
                        time.sleep(self.delay * retries)
                        continue
                    else:
                        logger.error(f"최대 재시도 횟수 초과 (Selenium 오류): {url}")
                        return False, None, url
            
            except Exception as e:
                logger.warning(f"예기치 않은 오류({retries+1}/{max_retries+1}): {url}, 오류: {e}")
                retries += 1
                if retries <= max_retries:
                    time.sleep(self.delay * retries)
                    continue
                else:
                    logger.error(f"최대 재시도 횟수 초과 (예기치 않은 오류): {url}")
                    return False, None, url
        
        # 모든 시도 실패 시
        logger.error(f"모든 재시도 실패: {url}")
        return False, None, url

    def detect_pagination(self, soup: Optional[BeautifulSoup] = None) -> Tuple[bool, Optional[Any]]:
        """페이지에서 페이지네이션 요소 감지"""
        if soup is not None:
            # BeautifulSoup으로 확인
            try:
                for selector in PAGINATION_SELECTORS:
                    elements = soup.select(selector)
                    if elements:
                        return True, elements[0]
                        
                return False, None
            except Exception as e:
                logger.error(f"BeautifulSoup으로 페이지네이션 감지 중 오류 발생: {e}")
                return False, None
        
        # Selenium 사용 필요한 경우
        try:
            # 페이지네이션 선택자 확인
            for selector in PAGINATION_SELECTORS:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements and len(elements) > 0:
                    return True, elements[0]
                    
            # 페이지 번호 패턴 확인
            for xpath in PAGE_NUMBER_PATTERNS:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements and len(elements) > 0:
                    return True, elements[0].find_element(By.XPATH, "./..")
                    
            return False, None
            
        except Exception as e:
            logger.error(f"Selenium으로 페이지네이션 감지 중 오류 발생: {e}")
            return False, None

    def handle_pagination(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """페이지네이션을 처리하여 모든 페이지 URL 반환"""
        pagination_urls = []
        
        # 현재 URL 정규화
        current_url = self.normalize_url(current_url)
        
        # 1. 페이지네이션 요소 감지
        has_pagination, pagination_element = self.detect_pagination(soup)
        
        # 페이지네이션 요소가 감지되었을 때 로그 출력
        if has_pagination:
            logger.debug(f"페이지네이션 요소 감지: {has_pagination}, URL: {current_url}")
        
        if not has_pagination:
            # 페이지네이션이 없어도 "더보기", "다음" 등의 링크 찾기
            more_links = soup.find_all('a', href=True, string=re.compile(r'(더보기|더\s*보기|다음|next|more)', re.IGNORECASE))
            for link in more_links:
                href = link['href']
                if href and href != '#' and not href.startswith('javascript:'):
                    full_url = urljoin(current_url, href)
                    if self.is_in_scope(full_url):
                        normalized_url = self.normalize_url(full_url)
                        if normalized_url not in pagination_urls and normalized_url != current_url:
                            pagination_urls.append(normalized_url)
                            logger.info(f"'더보기' 링크 발견: {normalized_url}")
            return pagination_urls
        
        # 2. 페이지 URL 패턴과 마지막 페이지 번호 파악
        url_pattern, last_page = self._extract_pagination_pattern(soup, current_url, pagination_element)
        
        # 페이지 수를 20으로 제한
        last_page = min(last_page, 25)
        
        logger.debug(f"URL 패턴: {url_pattern}, 마지막 페이지: {last_page}")
        
        # 3. 직접 페이지 링크 추가
        if pagination_element:
            for a in pagination_element.find_all('a', href=True):
                href = a['href']
                if href and href != '#':
                    if href.startswith('javascript:'):
                        # JavaScript 페이지네이션 처리는 복잡하므로 일단 스킵
                        continue
                    else:
                        # 일반 링크
                        full_url = urljoin(current_url, href)
                        if self.is_in_scope(full_url):
                            # URL 정규화 적용
                            normalized_url = self.normalize_url(full_url)
                            if normalized_url not in pagination_urls and normalized_url != current_url:
                                pagination_urls.append(normalized_url)
        
        # 4. URL 패턴이 있고 마지막 페이지 번호가 있는 경우, 모든 페이지 URL 생성
        if url_pattern and last_page > 0:
            for page_num in range(1, min(last_page + 1, 21)):  # 최대 20페이지로 제한
                page_url = url_pattern.replace('{page}', str(page_num))
                normalized_url = self.normalize_url(page_url)
                if normalized_url not in pagination_urls and normalized_url != current_url:
                    pagination_urls.append(normalized_url)
                    logger.info(f"패턴 기반 페이지네이션 URL 추가: {normalized_url}")
        
        # 페이지네이션 정보 로깅
        if pagination_urls:
            logger.info(f"[{len(self.visited_urls)}/{self.max_pages}] 페이지네이션 발견: {len(pagination_urls)}개 페이지")
        
        return pagination_urls

    def handle_javascript_pagination(self, url, js_code):
        """JavaScript 기반 페이지네이션 처리
        
        Args:
            url: 현재 URL
            js_code: JavaScript 페이지네이션 코드 (예: javascript:page_link('2'))
            
        Returns:
            페이지 내용 (BeautifulSoup)과 페이지 URL 또는 None, None (실패 시)
        """
        try:
            self._init_selenium()
            
            # 현재 페이지로 이동
            self.driver.get(url)
            
            # 페이지 로드 대기
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # JavaScript 코드에서 페이지 번호 추출
            match = re.search(r"page_link\('?(\d+)'?\)", js_code)
            if not match:
                return None, None
                
            page_num = match.group(1)

            # 페이지 변경 전 URL 기록
            original_url = self.driver.current_url
            
            # 직접 JavaScript 실행
            self.driver.execute_script(f"page_link({page_num})")
            
            # 페이지 변경 후 대기
            time.sleep(3)
            
            # 현재 페이지 내용과 URL 반환
            html_content = self.driver.page_source
            current_url = self.driver.current_url

            # 새 URL만 사용하도록 수정
            soup = BeautifulSoup(html_content, 'html.parser')

            logger.info(f"JS 페이지네이션 처리 결과: 새 URL: {current_url}")
            
            return soup, current_url
            
        except Exception as e:
            logger.error(f"JavaScript 페이지네이션 처리 중 오류: {e}")
            return None, None

    def _extract_pagination_pattern(self, soup: BeautifulSoup, current_url: str, pagination_element) -> Tuple[str, int]:
        """페이지네이션 URL 패턴과 마지막 페이지 번호 추출"""
        # 기본값 설정
        url_pattern = None
        last_page = 0
        
        try:
            # 1. 페이지 번호가 포함된 링크 찾기
            page_links = []
            if pagination_element:
                page_links = pagination_element.find_all('a', href=True)
            
            # 2. 페이지 번호와 해당 URL 추출
            page_numbers = []
            page_urls = {}
            
            for link in page_links:
                # 페이지 번호 추출 시도
                try:
                    page_num_text = link.get_text().strip()
                    if page_num_text.isdigit():
                        page_num = int(page_num_text)
                        href = link['href']
                        if href and href != '#' and not href.startswith('javascript:'):
                            full_url = urljoin(current_url, href)
                            page_numbers.append(page_num)
                            page_urls[page_num] = full_url
                        elif href.startswith('javascript:'):
                            # JavaScript 페이지네이션 처리 - 페이지 번호만 기록
                            page_numbers.append(page_num)
                            # 임시 URL 패턴 생성 (실제로는 실행되지 않음)
                            page_urls[page_num] = f"{current_url}?page={page_num}"
                except (ValueError, TypeError):
                    continue
            
            # 3. 마지막 페이지 번호 찾기
            if page_numbers:
                last_page = max(page_numbers)
            
            # 4. 페이지 URL 패턴 찾기
            if page_urls:
                # 페이지 번호 및 URL 패턴 파악
                url_pattern = self._find_url_pattern(page_urls)
            
            # 5. 마지막 페이지 번호가 없는 경우 대체 방법
            if last_page == 0:
                # "마지막" 또는 "Last" 링크 찾기
                last_links = soup.select('a.last, a.end, a:contains("마지막"), a:contains("Last")')
                for link in last_links:
                    href = link.get('href', '')
                    if href:
                        # URL에서 페이지 번호 추출 시도
                        try:
                            # JavaScript 링크 처리
                            if href.startswith('javascript:'):
                                js_match = re.search(r"page_link\('?(\d+)'?\)", href)
                                if js_match:
                                    last_page = int(js_match.group(1))
                                    break
                            
                            # 일반 URL 처리
                            parsed_url = urlparse(href)
                            query_params = parse_qs(parsed_url.query)
                            
                            for param in ['page', 'pageNo', 'pageIndex', 'p', 'pg']:
                                if param in query_params:
                                    last_page = int(query_params[param][0])
                                    break
                        except:
                            pass
                # JavaScript 페이지네이션에서 페이지 개수 추정 (추가)
                if last_page == 0:
                    js_links = [a['href'] for a in pagination_element.find_all('a', href=True) 
                            if a['href'].startswith('javascript:page_link')]
                    if js_links:
                        last_page = len(js_links)
            
            if url_pattern:
                logger.info(f"페이지네이션 패턴 추출: {url_pattern}, 마지막 페이지: {last_page}")
            else:
                logger.info(f"페이지네이션 패턴 추출 실패, 대체 방법 사용")
                
            return url_pattern, last_page
            
        except Exception as e:
            logger.error(f"페이지네이션 패턴 추출 중 오류: {e}")
            return None, 0

    def _find_url_pattern(self, page_urls: Dict[int, str]) -> str:
        """페이지 URL에서 일관된 패턴 찾기"""
        if len(page_urls) < 2:
            return None
        
        # 정렬된 페이지 번호와 URL
        sorted_pages = sorted(page_urls.items())
        
        # URL 분석
        patterns = []
        for page_num, url in sorted_pages:
            parsed = urlparse(url)
            path = parsed.path
            query = parse_qs(parsed.query)
            
            # 쿼리 매개변수에서 페이지 매개변수 찾기
            for param_name in ['page', 'pageNo', 'pageIndex', 'p', 'pg']:
                if param_name in query:
                    # URL 패턴 구성
                    query_copy = {k: v[0] if len(v) == 1 else v for k, v in query.items()}
                    query_copy[param_name] = '{page}'
                    
                    # 새 쿼리 문자열 생성
                    query_parts = []
                    for k, v in query_copy.items():
                        if isinstance(v, list):
                            for item in v:
                                query_parts.append(f"{k}={item}")
                        else:
                            query_parts.append(f"{k}={v}")
                    
                    new_query = '&'.join(query_parts)
                    pattern = f"{parsed.scheme}://{parsed.netloc}{path}?{new_query}"
                    patterns.append(pattern)
                    break
        
        # 가장 많이 발견된 패턴 반환
        if patterns:
            return max(set(patterns), key=patterns.count)
        
        return None

    def get_pagination_urls(self, soup: Optional[BeautifulSoup] = None, current_url: str = "") -> Set[str]:
        """페이지에서 모든 페이지네이션 URL 가져오기"""
        pagination_urls = set()
        
        # 현재 URL 정규화
        current_url = self.normalize_url(current_url)
        pagination_urls.add(current_url)
        
        try:
            # 페이지네이션 감지
            has_pagination, pagination_element = self.detect_pagination(soup)
            
            if not has_pagination:
                return pagination_urls
                
            # 페이지네이션 링크 추출
            if soup is not None:
                # BeautifulSoup으로 추출
                if pagination_element:
                    for a in pagination_element.find_all('a', href=True):
                        href = a['href']
                        if href and href != '#' and not href.startswith('javascript:'):
                            full_url = urljoin(current_url, href)
                            if self.is_in_scope(full_url):
                                # URL 정규화 적용
                                normalized_url = self.normalize_url(full_url)
                                pagination_urls.add(normalized_url)
                                
                # 다음 버튼 확인
                next_buttons = soup.select('a.next, a.nextpage, a[rel="next"]')
                for btn in next_buttons:
                    if btn.has_attr('href'):
                        href = btn['href']
                        if href and href != '#' and not href.startswith('javascript:'):
                            full_url = urljoin(current_url, href)
                            if self.is_in_scope(full_url):
                                # URL 정규화 적용
                                normalized_url = self.normalize_url(full_url)
                                pagination_urls.add(normalized_url)
            else:
                # Selenium으로 추출
                self._init_selenium()
                
                # 페이지네이션 요소에서 링크 가져오기
                page_links = []
                try:
                    if pagination_element:
                        page_links = pagination_element.find_elements(By.TAG_NAME, "a")
                except Exception:
                    # 대체 방법 시도
                    try:
                        page_links = self.driver.find_elements(
                            By.XPATH, 
                            "//a[contains(@href, 'page=') or contains(@href, 'pageIndex=') or contains(@href, 'pageNo=')]"
                        )
                    except Exception:
                        pass
                
                # 수집된 링크 처리
                for link in page_links:
                    try:
                        href = link.get_attribute('href')
                        if href and href != '#' and not href.startswith('javascript:'):
                            if self.is_in_scope(href):
                                # URL 정규화 적용
                                normalized_url = self.normalize_url(href)
                                pagination_urls.add(normalized_url)
                    except Exception:
                        continue
                
                # 다음 버튼 확인
                next_button_selectors = [
                    "a.next", "a.nextpage", "a[rel='next']", 
                    "//a[contains(text(), '다음')]", 
                    "//a[contains(text(), 'Next')]",
                    "//a[contains(@class, 'next')]"
                ]
                
                for selector in next_button_selectors:
                    try:
                        elements = []
                        if selector.startswith("//"):
                            elements = self.driver.find_elements(By.XPATH, selector)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                        if elements and len(elements) > 0:
                            href = elements[0].get_attribute('href')
                            if href and href != '#' and not href.startswith('javascript:'):
                                if self.is_in_scope(href):
                                    # URL 정규화 적용
                                    normalized_url = self.normalize_url(href)
                                    pagination_urls.add(normalized_url)
                            break
                    except Exception:
                        continue
                
            return pagination_urls
            
        except Exception as e:
            logger.error(f"페이지네이션 URL 수집 중 오류 발생: {e}")
            return pagination_urls

    def discover_urls(self, start_url: str, scope_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """정의된 범위 내의 모든 URL을 발견함.
        
        Args:
            start_url: 크롤링 시작 URL
            scope_patterns: 크롤링 범위를 제한하는 패턴 목록
            
        Returns:
            발견된 URL과 메타데이터가 포함된 딕셔너리
        """
        start_time = time.time()
        
        # 시작 URL 정규화
        start_url = self.normalize_url(start_url)
        
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc
        
        # 사이트맵 URL 추적을 위한 집합 초기화
        processed_sitemaps = set()
        
        # 범위 패턴 설정
        if scope_patterns:
            self.scope_patterns = [p.lower() for p in scope_patterns]
            logger.info(f"전달받은 범위 패턴 사용: {self.scope_patterns}")
        else:
            # 시작 URL 경로에서 범위 패턴 추출 (스마트 필터링)
            path_parts = parsed_url.path.lower().split('/')
            
            # 마지막 조각(파일명/페이지명) 제거
            if path_parts and path_parts[-1]:
                path_parts = path_parts[:-1]
            
            # 기본 범위 패턴을 시작 URL에서 추출
            extracted_patterns = []
            for part in path_parts:
                if part and part not in ['index.do', 'web', '']:
                    # /sites/ 경로는 제외
                    if part == 'sites':
                        continue
                    
                    # netloc에 이미 포함된 단어는 제외 (예: hansung)
                    if part in self.base_domain.lower():
                        continue
                    
                    # 유효한 패턴이면 대문자/소문자 버전 모두 추가
                    if part not in extracted_patterns:
                        extracted_patterns.append(part)
                        
                        # 대문자 버전도 추가 (원본 경로에서 찾기)
                        original_parts = parsed_url.path.split('/')
                        # 마지막 조각 제거 후 검색
                        if original_parts and original_parts[-1]:
                            original_parts = original_parts[:-1]
                        for original_part in original_parts:
                            if (original_part.lower() == part and 
                                original_part != part and 
                                original_part not in extracted_patterns):
                                extracted_patterns.append(original_part)
                                break
            
            # 추출된 패턴이 있으면 사용, 없으면 빈 패턴 (전체 도메인)
            if extracted_patterns:
                self.scope_patterns = extracted_patterns
                logger.info(f"시작 URL에서 범위 패턴 추출 (스마트 필터링): {self.scope_patterns}")
            else:
                # 범위 패턴이 없으면 도메인 전체 허용
                self.scope_patterns = ['']
                logger.info("범위 패턴이 추출되지 않아 도메인 전체를 범위로 설정")
        
        # 범위 패턴 검증 및 로깅
        logger.info(f"최종 적용된 범위 패턴: {self.scope_patterns}")
        if self.scope_patterns and self.scope_patterns != ['']:
            logger.info(f"범위 제한 활성화: {self.base_domain} 도메인에서 {self.scope_patterns} 패턴만 크롤링")
        else:
            logger.info(f"범위 제한 없음: {self.base_domain} 도메인 전체 크롤링")
        
        # 컬렉션 초기화 (스레드 안전)
        with self.url_lock:
            self.all_page_urls.clear()
            self.all_doc_urls.clear()
            self.visited_urls.clear()
            self.queued_urls.clear()
        
        saved_doc_urls = set()  # 이미 저장된 문서 URL 추적 (중복 방지)
        current_page = 0
        
        # 우선순위 큐 사용 (우선순위, URL, 부모URL)
        priority_queue = []
        heapq.heappush(priority_queue, (URLPriority.HIGH, start_url, None))
        
        # 큐 중복 방지
        with self.url_lock:
            self.queued_urls.add(start_url)
        
        # 파일 이름 생성을 위한 타임스탬프와 범위 이름 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        scope_name = '_'.join(self.scope_patterns) if self.scope_patterns else 'full_domain'
        
        # 도메인 디렉토리 생성
        domain_name = self.base_domain.replace('.', '_')
        domain_base_dir = os.path.join(BASE_DIR, f"{timestamp}_{domain_name}_{scope_name}")
        domain_dir = domain_base_dir
        os.makedirs(domain_dir, exist_ok=True)
        
        # 크롤링 전용 로그 파일 핸들러 추가
        log_file = os.path.join(domain_dir, f"crawling_log_{timestamp}.txt")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        logger.info(f"크롤링 로그 파일 생성: {log_file}")
        
        # 증분 저장을 위한 파일 경로 설정
        page_urls_file = os.path.join(domain_dir, f"page_urls_{timestamp}.txt")
        doc_urls_file = os.path.join(domain_dir, f"document_urls_{timestamp}.txt")
        
        # 증분 저장을 위한 카운터
        page_urls_batch = []
        doc_urls_batch = set()  # 중복 방지를 위해 set 사용
        increment_size = 50  # 50개씩 증분 저장
        
        logger.info(f"URL 발견 시작: {start_url}")
        logger.info(f"기본 도메인: {self.base_domain}")
        logger.info(f"범위 패턴: {self.scope_patterns}")
        logger.info(f"최대 페이지: {self.max_pages}")
        
        # 사이트맵 자동 발견 및 처리 추가
        self._discover_and_process_sitemaps(priority_queue, processed_sitemaps)
        
        try:
            # 병렬 처리를 위한 설정
            max_workers = min(10, os.cpu_count() or 4)  # CPU 코어 수에 따라 워커 수 조정 or 4
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 병렬 크롤링
                while priority_queue and current_page < self.max_pages:
                    # 배치 크기 설정 (병렬 처리할 URL 수)
                    batch_size = min(max_workers, len(priority_queue), self.max_pages - current_page)
                    
                    # 배치 처리할 URL 목록 (우선순위 순으로)
                    batch_urls = []
                    batch_parents = []
                    batch_priorities = []
                    
                    for _ in range(batch_size):
                        if priority_queue:
                            priority, url, parent = heapq.heappop(priority_queue)
                            url = self.normalize_url(url)
                            
                            # 이미 방문했거나 범위 밖인 URL 건너뛰기 (원자적 체크)
                            with self.url_lock:
                                if url in self.visited_urls or not self.is_in_scope(url):
                                    continue
                                # 방문 표시 (원자적)
                                self.visited_urls.add(url)
                                
                            # 배치에 URL 추가
                            batch_urls.append(url)
                            batch_parents.append(parent)
                            batch_priorities.append(priority)
                    
                    if not batch_urls:
                        continue
                        
                    # 진행 상황 추적
                    current_page += len(batch_urls)
                    progress = f"[{current_page}/{self.max_pages}]"
                    logger.info(f"{progress} 배치 처리 중: {len(batch_urls)}개 URL")
                    
                    # URL 병렬 처리
                    future_to_url = {executor.submit(self._process_url, url, parent): (url, priority) 
                                    for url, parent, priority in zip(batch_urls, batch_parents, batch_priorities)}
                    
                    for future in as_completed(future_to_url):
                        url, priority = future_to_url[future]
                        try:
                            result = future.result()
                            if result:
                                page_links, doc_links, pagination_links, current_url, is_list_page = result
                                
                                # 현재 URL이 문서 URL인지 확인
                                is_current_url_document = self.is_valid_file_url(url, url)
                                
                                # 페이지 URL 저장 (문서 URL이 아니고 게시판 목록 페이지가 아닌 경우에만)
                                if not is_current_url_document and not is_list_page:
                                    with self.url_lock:
                                        if self.add_url_atomically(url, self.all_page_urls):
                                            page_urls_batch.append(url)
                                elif is_list_page:
                                    # 게시판 목록 페이지는 URL 목록에 저장하지 않음
                                    logger.info(f"[{len(self.visited_urls)}/{self.max_pages}] 게시판 목록 페이지 (URL 목록 제외): {url}")
                                else:
                                    # 현재 URL이 문서 URL인 경우 문서 URL 집합에 추가
                                    with self.url_lock:
                                        if self.add_url_atomically(url, self.all_doc_urls):
                                            doc_urls_batch.add(url)
                                            logger.info(f"[{len(self.visited_urls)}/{self.max_pages}] 현재 URL이 문서: {url}")
                                
                                # 추출된 문서 URL 중복 제거 및 저장 (원자적)
                                new_doc_urls = set()
                                for doc_url in doc_links:
                                    normalized_doc_url = self.normalize_url(doc_url)
                                    if normalized_doc_url:
                                        # 스레드 안전한 중복 체크
                                        with self.url_lock:
                                            if self.add_url_atomically(normalized_doc_url, self.all_doc_urls):
                                                new_doc_urls.add(normalized_doc_url)
                                                logger.info(f"[{len(self.visited_urls)}/{self.max_pages}] 새 문서 발견: {normalized_doc_url}")
                                
                                # 배치에 새로운 문서 URL만 추가
                                doc_urls_batch.update(new_doc_urls)
                                
                                # 새 URL을 우선순위 큐에 추가 (현재 URL을 부모로 설정)
                                for link in page_links:
                                    normalized_link = self.normalize_url(link)
                                    with self.url_lock:
                                        if (normalized_link not in self.visited_urls and 
                                            normalized_link not in self.queued_urls):
                                            heapq.heappush(priority_queue, (URLPriority.NORMAL, normalized_link, current_url))
                                            self.queued_urls.add(normalized_link)
                                
                                # 페이지네이션 URL은 낮은 우선순위로 추가
                                for link in pagination_links:
                                    normalized_link = self.normalize_url(link)
                                    with self.url_lock:
                                        if (normalized_link not in self.visited_urls and 
                                            normalized_link not in self.queued_urls):
                                            heapq.heappush(priority_queue, (URLPriority.LOW, normalized_link, current_url))
                                            self.queued_urls.add(normalized_link)
                                            
                        except Exception as e:
                            logger.error(f"URL 처리 결과 처리 중 오류 발생: {url}, {e}")
                            # 실패한 URL을 방문 목록에서 제거 (재시도 가능하도록)
                            with self.url_lock:
                                self.visited_urls.discard(url)
                    
                    # 증분 페이지 URL 저장
                    if len(page_urls_batch) >= increment_size:
                        self._save_incrementally(page_urls_batch, page_urls_file)
                        page_urls_batch = []
                    
                    # 증분 문서 URL 저장 (중복 제거 후)
                    if len(doc_urls_batch) >= increment_size:
                        # 이미 저장된 문서 URL 제외
                        new_docs_to_save = doc_urls_batch - saved_doc_urls
                        if new_docs_to_save:
                            self._save_incrementally(list(new_docs_to_save), doc_urls_file)
                            saved_doc_urls.update(new_docs_to_save)
                            logger.info(f"문서 URL 증분 저장: {len(new_docs_to_save)}개 (중복 제거됨)")
                        doc_urls_batch = set()
                    
                    # 요청 간 지연 추가 (배치 간 지연)
                    time.sleep(self.delay)
                
                # 남은 URL 저장
                if page_urls_batch:
                    self._save_incrementally(page_urls_batch, page_urls_file)
                
                if doc_urls_batch:
                    # 이미 저장된 문서 URL 제외
                    new_docs_to_save = doc_urls_batch - saved_doc_urls
                    if new_docs_to_save:
                        self._save_incrementally(list(new_docs_to_save), doc_urls_file)
                        saved_doc_urls.update(new_docs_to_save)
                        logger.info(f"최종 문서 URL 저장: {len(new_docs_to_save)}개 (중복 제거됨)")
            
            # 결과 검증 단계
            validation_results = self._validate_results()
            
            # 실행 시간 계산
            execution_time = time.time() - start_time
            
            # 메타데이터 결과 JSON 저장
            json_data = {
                "timestamp": timestamp,
                "execution_time_seconds": execution_time,
                "base_url": start_url,
                "base_domain": self.base_domain,
                "scope_patterns": self.scope_patterns,
                "scope_name": scope_name,
                "total_pages_discovered": len(self.all_page_urls),
                "total_documents_discovered": len(self.all_doc_urls),
                "unique_documents_saved": len(saved_doc_urls),
                "normalization_cache_size": self.normalization_cache.size(),
                "validation_results": validation_results,
            }
            
            json_file = os.path.join(domain_dir, f"crawl_results_{timestamp}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"\nURL 발견 완료:")
            logger.info(f"발견된 페이지: {len(self.all_page_urls)}개, 문서: {len(self.all_doc_urls)}개")
            logger.info(f"저장된 고유 문서: {len(saved_doc_urls)}개")
            logger.info(f"정규화 캐시 크기: {self.normalization_cache.size()}개")
            logger.info(f"결과 저장 위치: {domain_dir}")
            logger.info(f"실행 시간: {execution_time:.1f}초")
            
            return {
                "json_data": json_data,
                "page_urls": self.all_page_urls,
                "doc_urls": self.all_doc_urls,
                "results_dir": domain_dir,
                "json_file": json_file,
                "log_file": log_file,
                "execution_time": execution_time,
                "unique_documents_saved": len(saved_doc_urls),
                "validation_results": validation_results,
                # 호출하는 쪽에서 쉽게 접근할 수 있도록 최상위 레벨에도 추가
                "base_domain": self.base_domain,
                "scope_patterns": self.scope_patterns,
                "total_pages_discovered": len(self.all_page_urls),
                "total_documents_discovered": len(self.all_doc_urls)
            }
        
        except Exception as e:
            logger.error(f"URL 발견 실패: {e}")
            return {
                "page_urls": self.all_page_urls,
                "doc_urls": self.all_doc_urls,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        
        finally:
            # 로그 핸들러 정리
            if 'file_handler' in locals():
                logger.removeHandler(file_handler)
                file_handler.close()
                logger.info(f"크롤링 로그 저장 완료: {log_file}")
            
            # 드라이버 종료 
            self.close_driver()

    def _save_incrementally(self, urls: List[str], filepath: str) -> None:
        """URL 목록을 파일에 증분식으로 추가"""
        try:
            # 파일에 URL 추가
            with open(filepath, 'a', encoding='utf-8') as f:
                for url in urls:
                    f.write(f"{url}\n")
            logger.info(f"증분 저장 완료: {len(urls)}개 URL을 {filepath}에 추가")
        except Exception as e:
            logger.error(f"증분 저장 중 오류 발생: {e}")

    def is_sitemap_url(self, url: str) -> bool:
        """URL이 사이트맵 페이지인지 확인"""
        lower_url = url.lower()
        return ('sitemap' in lower_url or 'site-map' in lower_url or 'site_map' in lower_url)
    
    def handle_sitemap(self, url: str) -> Set[str]:
        """사이트맵 페이지에서 모든 링크를 추출하여 집합으로 반환"""
        sitemap_links = set()
        
        # URL 정규화
        url = self.normalize_url(url)
        
        # 사이트맵 페이지 가져오기
        success, content, current_url = self.fetch_page(url)
        if not success:
            logger.error(f"사이트맵 가져오기 실패: {url}")
            return sitemap_links
        
        try:
            # 사이트맵 콘텐츠 파싱
            if isinstance(content, BeautifulSoup):
                soup = content
            else:
                # Selenium을 사용한 경우 페이지 소스 가져오기
                self._init_selenium()
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
            
            # 사이트맵 특정 구조 찾기
            # 1. 표준 사이트맵 목록
            sitemap_containers = soup.select('.sitemap, .site-map, #sitemap, #site-map, [class*="sitemap"], [id*="sitemap"]')
            
            # 2. 찾지 못한 경우, 사이트 구조를 포함할 수 있는 일반적인 요소 찾기
            if not sitemap_containers:
                sitemap_containers = soup.select('nav, .nav, .navigation, .menu, .main-menu, ul.depth_1, .gnb, .lnb')
            
            # 3. 여전히 찾지 못한 경우, 전체 본문 사용
            if not sitemap_containers:
                sitemap_containers = [soup.find('body')]
            
            # 각 컨테이너에서 링크 추출
            for container in sitemap_containers:
                if container:
                    links = container.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        if href and href != '#' and not href.startswith('javascript:'):
                            # 상대 경로 처리 개선
                            if href.startswith('/'):
                                # 도메인 앞부분 추가
                                full_url = f"https://{self.base_domain}{href}"
                            else:
                                full_url = urljoin(url, href)
                            
                            # 디버깅용 로그 추가
                            logger.debug(f"사이트맵 링크 변환: {href} -> {full_url}")
                            
                            if self.is_in_scope(full_url) and not self.should_exclude_url(full_url):
                                # URL 정규화 적용
                                normalized_url = self.normalize_url(full_url)
                                sitemap_links.add(normalized_url)
                            else:
                                # 범위 밖 사이트맵 링크 로깅
                                logger.debug(f"범위 밖 사이트맵 링크 제외: {full_url}")
            
            logger.info(f"사이트맵에서 {len(sitemap_links)}개 링크 추출: {url}")
            
            # XML 사이트맵 링크도 확인
            xml_sitemap_links = soup.select('a[href*="sitemap.xml"]')
            if xml_sitemap_links:
                for link in xml_sitemap_links:
                    href = link.get('href')
                    if href:
                        xml_url = urljoin(url, href)
                        # XML 사이트맵 URL도 정규화
                        xml_url = self.normalize_url(xml_url)
                        xml_links = self.parse_xml_sitemap(xml_url)
                        sitemap_links.update(xml_links)
                        
            return sitemap_links
            
        except Exception as e:
            logger.error(f"사이트맵 처리 중 오류 발생 {url}: {e}")
            return sitemap_links

    def parse_xml_sitemap(self, url: str) -> Set[str]:
        """XML 사이트맵을 파싱하고 모든 URL 추출"""
        xml_links = set()
        
        # URL 정규화
        url = self.normalize_url(url)
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                url_tags = soup.find_all('loc')
                
                for tag in url_tags:
                    link = tag.text.strip()
                    if self.is_in_scope(link) and not self.should_exclude_url(link):
                        # URL 정규화 적용
                        normalized_url = self.normalize_url(link)
                        xml_links.add(normalized_url)
                    else:
                        # 범위 밖 XML 사이트맵 링크 로깅
                        logger.debug(f"범위 밖 XML 사이트맵 링크 제외: {link}")
                
                logger.info(f"XML 사이트맵에서 {len(xml_links)}개 링크 추출: {url}")
            
            return xml_links
            
        except Exception as e:
            logger.error(f"XML 사이트맵 파싱 중 오류 발생 {url}: {e}")
            return xml_links

    def _process_url(self, url: str, parent_url: Optional[str] = None) -> Optional[Tuple[List[str], List[str], List[str], str, bool]]:
        """URL을 처리하고 발견된 링크, 문서 URL, 페이지네이션 URL을 반환합니다.
        병렬 처리를 위해 독립적인 메서드로 구현됨.
        
        Args:
            url: 처리할 URL
            parent_url: 현재 URL의 부모 URL (사용하지 않음, 호환성을 위해 유지)
            
        Returns:
            (일반 링크 목록, 문서 링크 목록, 페이지네이션 링크 목록, 현재 URL, 목록 페이지 여부) 튜플 또는 None (오류 시)
        """
        try:
            # 사이트맵 URL 처리
            if self.is_sitemap_url(url):
                sitemap_links = self.handle_sitemap(url)
                logger.info(f"사이트맵 처리 완료: {url}, 발견된 링크: {len(sitemap_links)}개")
                return list(sitemap_links), [], [], url, False
            
            # 페이지 가져오기
            success, content, current_url = self.fetch_page(url)
            
            if not success:
                return None
            
            # 정규화된 URL로 업데이트
            url = self.normalize_url(current_url)
            
            # 게시판 목록 페이지인지 확인
            is_list_page = self.is_list_page(url)
            
            # BeautifulSoup으로 페이지 파싱
            if isinstance(content, BeautifulSoup):
                soup = content
            else:
                # Selenium 결과 사용
                self._init_selenium()
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
            
            # 링크 추출
            links, documents = self.extract_links(soup, url)
            
            # 페이지네이션 처리
            pagination_urls = self.handle_pagination(soup, url)
            
            return list(links), list(documents), list(pagination_urls), url, is_list_page
            
        except Exception as e:
            logger.error(f"URL 처리 중 오류 발생: {url}, {e}")
            return None

    def _validate_results(self) -> Dict[str, Any]:
        """크롤링 결과 검증"""
        validation_results = {
            "duplicate_pages_found": 0,
            "duplicate_docs_found": 0,
            "invalid_urls_found": 0,
            "scope_violations_found": 0
        }
        
        try:
            # 1. 페이지 URL 중복 검사
            page_url_list = list(self.all_page_urls)
            unique_pages = set(page_url_list)
            validation_results["duplicate_pages_found"] = len(page_url_list) - len(unique_pages)
            
            # 2. 문서 URL 중복 검사
            doc_url_list = list(self.all_doc_urls)
            unique_docs = set(doc_url_list)
            validation_results["duplicate_docs_found"] = len(doc_url_list) - len(unique_docs)
            
            # 3. URL 유효성 검사
            invalid_urls = 0
            scope_violations = 0
            
            for url in self.all_page_urls.union(self.all_doc_urls):
                try:
                    parsed = urlparse(url)
                    if not parsed.scheme or not parsed.netloc:
                        invalid_urls += 1
                    elif not self.is_in_scope(url):
                        scope_violations += 1
                except Exception:
                    invalid_urls += 1
            
            validation_results["invalid_urls_found"] = invalid_urls
            validation_results["scope_violations_found"] = scope_violations
            
            # 검증 결과 로깅
            if any(validation_results.values()):
                logger.warning(f"검증 결과: {validation_results}")
            else:
                logger.info("모든 검증 통과")
                
        except Exception as e:
            logger.error(f"결과 검증 중 오류 발생: {e}")
            validation_results["validation_error"] = str(e)
        
        return validation_results

    def _discover_and_process_sitemaps(self, priority_queue, processed_sitemaps):
        """사이트맵 자동 발견 및 처리 (우선순위 큐 사용)"""
        base_url = f"https://{self.base_domain}"
        
        # 1. 표준 사이트맵 URL들 확인
        sitemap_urls = [
            f"{base_url}/sitemap.xml",
            f"{base_url}/sitemap_index.xml",
            f"{base_url}/sitemaps.xml",
            f"{base_url}/sitemap/index.xml"
        ]
        
        logger.info("사이트맵 자동 발견 시작...")
        
        # 2. robots.txt에서 사이트맵 찾기
        try:
            robots_url = f"{base_url}/robots.txt"
            response = self.session.get(robots_url, timeout=self.timeout)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    line = line.strip()
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        if sitemap_url not in sitemap_urls:
                            sitemap_urls.append(sitemap_url)
                            logger.info(f"robots.txt에서 사이트맵 발견: {sitemap_url}")
        except Exception as e:
            logger.debug(f"robots.txt 확인 중 오류: {e}")
        
        # 3. 각 사이트맵 URL 처리
        for sitemap_url in sitemap_urls:
            if sitemap_url not in processed_sitemaps:
                processed_sitemaps.add(sitemap_url)
                
                # XML 사이트맵인 경우 직접 파싱
                if sitemap_url.endswith('.xml'):
                    try:
                        xml_links = self.parse_xml_sitemap(sitemap_url)
                        if xml_links:
                            logger.info(f"XML 사이트맵에서 {len(xml_links)}개 URL 발견: {sitemap_url}")
                            for link in xml_links:
                                with self.url_lock:
                                    if link not in self.queued_urls and self.is_in_scope(link):
                                        heapq.heappush(priority_queue, (URLPriority.HIGH, link, None))
                                        self.queued_urls.add(link)
                                    elif link not in self.queued_urls:
                                        logger.debug(f"범위 밖 XML 사이트맵 링크 큐 추가 제외: {link}")
                    except Exception as e:
                        logger.debug(f"XML 사이트맵 처리 중 오류 {sitemap_url}: {e}")
                else:
                    # HTML 사이트맵인 경우 우선순위 큐에 추가
                    with self.url_lock:
                        if sitemap_url not in self.queued_urls:
                            heapq.heappush(priority_queue, (URLPriority.HIGH, sitemap_url, None))
                            self.queued_urls.add(sitemap_url)
                            logger.info(f"HTML 사이트맵 큐에 추가: {sitemap_url}")
        
        # 4. 일반적인 사이트맵 페이지 URL들도 확인
        common_sitemap_pages = [
            f"{base_url}/sitemap",
            f"{base_url}/site-map", 
            f"{base_url}/sitemap.html",
            f"{base_url}/map"
        ]
        
        for page_url in common_sitemap_pages:
            with self.url_lock:
                if page_url not in self.queued_urls:
                    heapq.heappush(priority_queue, (URLPriority.HIGH, page_url, None))
                    self.queued_urls.add(page_url)
                    logger.debug(f"사이트맵 페이지 후보 추가: {page_url}")
        
        logger.info(f"사이트맵 자동 발견 완료. 총 {len(sitemap_urls)}개 사이트맵 URL 처리됨.")

def main(start_url, scope=None, max_pages=1000, delay=1.0, timeout=20, use_requests=True, verbose=False):
    """매개변수로 크롤러 실행
    
    Args:
        start_url (str): 크롤링 시작 URL
        scope (List[str], optional): 크롤링 범위 제한 (예: ["cse", "department"])
        max_pages (int, optional): 크롤링할 최대 페이지 수. 기본값은 1000
        delay (float, optional): 요청 간 지연 시간(초). 기본값은 1.0초
        timeout (int, optional): 페이지 로딩 시간 제한(초). 기본값은 20초
        use_requests (bool, optional): 간단한 페이지는 requests 사용 여부. 기본값은 True
        verbose (bool, optional): 자세한 로깅 활성화 여부. 기본값은 False
    
    Returns:
        Dict[str, Any]: 크롤링 결과와 메타데이터
    """
    # 로깅 레벨 구성
    if verbose:
        logger.setLevel(logging.DEBUG)
        
    logger.info(f"URL 크롤러 시작: {start_url}")
    logger.info(f"범위 패턴: {scope}")
    logger.info(f"설정 - 최대 페이지: {max_pages}, 지연: {delay}초, 타임아웃: {timeout}초")
    
    # 컨텍스트 매니저를 사용한 크롤러 생성 및 실행
    try:
        with ScopeLimitedCrawler(
            max_pages=max_pages, 
            delay=delay, 
            timeout=timeout,
            use_requests=use_requests
        ) as crawler:
            results = crawler.discover_urls(start_url, scope)
            
            if results and "error" not in results:
                logger.info("\n=== 크롤링 요약 ===")
                logger.info(f"발견된 페이지: {len(results['page_urls'])}개")
                logger.info(f"발견된 문서: {len(results['doc_urls'])}개")
                logger.info(f"저장된 고유 문서: {results.get('unique_documents_saved', 0)}개")
                logger.info(f"정규화 캐시 효율성: {results.get('normalization_cache_size', 0)}개 캐시됨")
                logger.info(f"결과 저장 위치: {results['results_dir']}")
                logger.info(f"실행 시간: {results.get('execution_time', 0):.1f}초")
                
                # 검증 결과 출력
                validation = results.get('validation_results', {})
                if validation:
                    logger.info(f"검증 결과: {validation}")
                
                # 성능 통계
                total_urls = len(results['page_urls']) + len(results['doc_urls'])
                if results.get('execution_time', 0) > 0:
                    urls_per_second = total_urls / results['execution_time']
                    logger.info(f"처리 속도: {urls_per_second:.1f} URLs/초")
            else:
                logger.error(f"크롤링 실패: {results.get('error', '알 수 없는 오류')}")
            
            return results

    except KeyboardInterrupt:
        logger.info("사용자에 의해 크롤링 중단됨")
        return {"error": "사용자 중단", "interrupted": True}
    except Exception as e:
        logger.error(f"크롤링 실패: {e}")
        return {"error": str(e), "execution_time": 0}


if __name__ == "__main__":
    try:
        # 크롤링 실행
        results = main(
            # start_url="https://hansung.ac.kr/sites/CSE/index.do",
            # start_url="https://hansung.ac.kr/sites/hansung/index.do",
            # start_url="https://dorm.hansung.ac.kr/kor/index.do",
            max_pages=100000,
            delay=1.0,
            timeout=20,
            use_requests=True,
            verbose=True
        )
        
        # 결과 출력
        if results and "error" not in results:
            print(f"\n✅ 크롤링 성공!")
            print(f"📄 페이지: {len(results.get('page_urls', []))}개")
            print(f"📎 문서: {len(results.get('doc_urls', []))}개")
            print(f"⏱️  실행시간: {results.get('execution_time', 0):.1f}초")
            print(f"📁 결과 위치: {results.get('results_dir', 'N/A')}")
        else:
            print(f"\n❌ 크롤링 실패: {results.get('error', '알 수 없는 오류')}")
            
    except KeyboardInterrupt:
        print("\n⏹️  크롤링 중단됨")
    except Exception as e:
        print(f"\n💥 오류: {e}")