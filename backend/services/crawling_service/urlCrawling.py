# 경고 필터 설정 (soupsieve deprecated 경고 무시)
import warnings
warnings.filterwarnings("ignore", message="The pseudo class ':contains' is deprecated", category=FutureWarning)

# matplotlib 백엔드 설정 (GUI 스레드 오류 방지)
import matplotlib
matplotlib.use('Agg')  # GUI가 없는 백엔드 사용

# 웹 크롤링 관련
from bs4 import BeautifulSoup   # html 파싱 + 데이터 추출 : find_all(조건에 맞는 모든 태그 찾기), select(css 선택자 사용)
import requests                                         # 정적 웹페이지 크롤링: 웹 요청 처리(get, post) + 웹 페이지 다운로드(text, json)
from requests.exceptions import Timeout, HTTPError, RequestException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# 시스템 및 유틸리티
import os, time, random, re, json, logging, base64                 
from urllib.parse import urlparse, urljoin, parse_qs
from datetime import datetime
from typing import Set, List, Dict, Tuple, Optional, Any
import threading                                        # 스레드 안전성을 위한 락

from pathlib import Path
try:
    from .simple_visualizer import SimpleTreeVisualizer
    from .crawler_constants import (
        BASE_DIR, USER_AGENTS, DOC_EXTENSIONS, EXCLUDE_PATTERNS, 
        LIST_PAGE_PATTERNS, EXCLUDE_EXTENSIONS, PAGINATION_SELECTORS,
        PAGE_NUMBER_PATTERNS, ATTACHMENT_CLASSES, DOWNLOAD_PATTERNS,
        EXPLICIT_DOWNLOAD_PATTERNS, ERROR_PATTERNS
    )
except ImportError:
    # 직접 실행할 때를 위한 절대 import
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from simple_visualizer import SimpleTreeVisualizer
    from crawler_constants import (
        BASE_DIR, USER_AGENTS, DOC_EXTENSIONS, EXCLUDE_PATTERNS, 
        LIST_PAGE_PATTERNS, EXCLUDE_EXTENSIONS, PAGINATION_SELECTORS,
        PAGE_NUMBER_PATTERNS, ATTACHMENT_CLASSES, DOWNLOAD_PATTERNS,
        EXPLICIT_DOWNLOAD_PATTERNS, ERROR_PATTERNS
    )

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

"""URL 정규화 결과를 캐싱하는 스레드 안전한 캐시 구현"""
class URLNormalizationCache:
    def __init__(self):
        self.cache = {}  # 단순 딕셔너리 - URL 중복 방지를 위해 무제한 저장
        self.lock = threading.RLock()   # 스레드 안전성을 위한 재진입 가능한 락
    
    #캐시 조회
    def get(self, key: str) -> Optional[str]:
        with self.lock:
            return self.cache.get(key)
    
    #캐시 추가
    def put(self, key: str, value: str) -> None:
        with self.lock:
            self.cache[key] = value
    
    #캐시 초기화
    def clear(self) -> None:
        with self.lock:
            self.cache.clear()
    
    #캐시 크기 반환
    def size(self) -> int:
        with self.lock:
            return len(self.cache)

"""URL들을 트리 노드로 표현하는 클래스"""
class URLTreeNode:
    #URL, 부모, 깊이 초기화
    def __init__(self, url: str, parent: Optional['URLTreeNode'] = None, depth: int = 0):
        self.url = url
        self.parent = parent
        self.children: List['URLTreeNode'] = []
        self.depth = depth
        self.is_document = False
        self.page_title = ""
        self.visited_at = None          #방문 시간
        self.doc_links: List[str] = []
        
        # 웹사이트 구조 분석을 위한 추가 속성들
        self.page_type = ""  # "main", "category", "board", "article", "document" 등
        self.breadcrumb = "unknown"  # 현재 페이지의 계층적 구조 (브레드크럼)
        self.link_count = 0  # 해당 페이지에서 발견된 링크 수

        self.load_time = 0.0  # 페이지 로딩 시간
        self.file_size = 0  # 페이지 크기 (bytes)
        
        # 논리적 구조 vs 물리적 연결 구분
        self.logical_parent = None  # 네비게이션 기반 논리적 부모
        self.logical_children = []  # 네비게이션 기반 논리적 자식들
        self.navigation_links = []  # 네비게이션/메뉴에서 발견된 링크들
        self.content_links = []    # 콘텐츠에서 발견된 링크들
        self.navigation_level = 0  # 네비게이션 기반 계층 레벨
        self.is_navigation_node = False  # 네비게이션 구조의 핵심 노드인지
        self.menu_position = ""    # 메뉴에서의 위치 (header, sidebar, footer 등)
    
    #자식 노드 추가
    def add_child(self, child_url: str) -> 'URLTreeNode':
        
        child_node = URLTreeNode(child_url, self, self.depth + 1)
        
        # URL 패턴으로 문서 파일 여부 미리 확인
        if self._is_likely_document_url(child_url):
            child_node.is_document = True
            child_node.page_type = "document"
            # 문서 파일의 경우 기본 브레드크럼 설정
            if self.breadcrumb and self.breadcrumb not in ["unknown", "홈"]:
                child_node.breadcrumb = f"{self.breadcrumb}/첨부파일"
            else:
                child_node.breadcrumb = "첨부파일"
        
        self.children.append(child_node)
        return child_node
    
    #URL 패턴으로 문서 파일 가능성 확인
    def _is_likely_document_url(self, url: str) -> bool:
        """URL 패턴으로 문서 파일 가능성 확인"""
        try:
            url_lower = url.lower()
            
            # 명확한 다운로드 패턴
            if any(pattern in url_lower for pattern in ['download.do', 'filedown.do', 'getfile.do']):
                return True
            
            # 파일 확장자 확인
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # 문서 파일 확장자
            doc_extensions = ['.pdf', '.docx', '.doc', '.hwp', '.txt', '.hwpx', '.xls', '.xlsx', '.ppt', '.pptx']
            if any(path.endswith(ext) for ext in doc_extensions):
                return True
            
            # 첨부파일 관련 경로
            if any(keyword in path for keyword in ['/attach', '/file', '/download']):
                return True
            
            return False
            
        except Exception:
            return False

    #루트부터 현재 노드까지의 경로 반환
    def get_path_from_root(self) -> List[str]:
        path = []
        current = self
        while current:
            path.insert(0, current.url)
            current = current.parent
        return path
    
    #URL에서 의미있는 세그먼트를 추출하여 메뉴 경로 구성에 활용
    def _extract_meaningful_url_segment(self) -> str:
        """URL에서 의미있는 세그먼트를 추출하여 메뉴 경로 구성에 활용"""
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.url)
            
            # 쿼리 파라미터에서 의미있는 정보 추출
            query_params = parse_qs(parsed.query)
            
            # artclView.do 같은 게시글 보기 페이지인 경우
            if 'artclView.do' in self.url:
                if 'artclNo' in query_params:
                    return f"게시글_{query_params['artclNo'][0]}"
                return "게시글"
            
            # 다운로드 파일인 경우
            if self.is_document or any(pattern in self.url.lower() for pattern in ['download', 'file']):
                return "첨부파일"
            
            # URL 경로에서 의미있는 부분 추출
            path_parts = [p for p in parsed.path.split('/') if p and p not in ['index.do', 'main.do']]
            if path_parts:
                last_part = path_parts[-1]
                # 파일 확장자 제거
                clean_part = re.sub(r'\.(do|html|htm|jsp|php)$', '', last_part)
                
                # 의미있는 이름으로 변환
                segment_mappings = {
                    'notice': '공지사항',
                    'news': '소식',
                    'intro': '소개',
                    'about': '소개'
                }
                
                return segment_mappings.get(clean_part.lower(), clean_part)
            
            return ""
            
        except Exception as e:
            logger.debug(f"URL 세그먼트 추출 실패: {e}")
            return ""
    
    #페이지 타입 분류
    def classify_page_type(self, soup: BeautifulSoup, start_url: str = None) -> str:
        """페이지 타입을 4개 카테고리로 간소화하여 분류: Main, document, board, general"""
        try:
            url_lower = self.url.lower()
            
            # 🏠 Main 페이지: start_url과 정확히 일치하는 경우만 (One and Only)
            if start_url and self.url == start_url:
                return "main"
            
            # 📄 Document: 다운로드/파일 관련 패턴 (최우선)
            if any(pattern in url_lower for pattern in EXPLICIT_DOWNLOAD_PATTERNS):
                return "document"
            
            # 📄 Document: 문서 파일 속성 기반
            if self.is_document:
                return "document"
            
            # 📋 Board: 게시판 관련 패턴
            if any(pattern in url_lower for pattern in ['board', 'bbs', 'list', 'artcllist']):
                # 다운로드 패턴이 포함된 게시판 URL은 문서로 분류
                if any(dl_pattern in url_lower for dl_pattern in EXPLICIT_DOWNLOAD_PATTERNS):
                    return "document"
                else:
                    return "board"
            
            # 📋 Board: 콘텐츠 기반 게시판 감지 (테이블 구조)
            if soup:
                page_text = soup.get_text().lower()
                tables = soup.find_all('table')
                if len(tables) >= 2:
                    # 게시판 특성 키워드 확인
                    board_keywords = ['번호', '제목', '작성자', '날짜', '조회', 'subject', 'date', 'view']
                    if any(keyword in page_text for keyword in board_keywords):
                        return "board"
            
            # 🌐 General: 나머지 모든 페이지
            return "general"
            
        except Exception as e:
            logger.debug(f"페이지 타입 분류 중 오류: {e}")
            return "general"
    
    """전체적인 브레드크럼 추출 프로세스를 관리하는 메인 함수로 외부에서 호출"""
    #현재 페이지의 계층적 구조 반환. 1. 네비게이션 메뉴에서 찾기 2. URL 패턴 기반 추정
    def extract_breadcrumb(self, soup: BeautifulSoup, current_url: str) -> str:
        try:
            if not soup:
                return "unknown"
            
            # 메인 네비게이션 컨테이너 찾기
            nav_containers = soup.select([
                'nav', '.nav', '.main-menu', '.gnb', '.lnb', '.menu',
                '[class*="menu"]', '[id*="menu"]', '[class*="nav"]', '[id*="nav"]'
            ])
            
            for nav in nav_containers:
                hierarchy_path = self._extract_hierarchy_from_nav(nav, current_url)
                if hierarchy_path != "unknown":
                    logger.debug(f"🎯 메뉴 계층 추출 성공: {hierarchy_path} for {current_url}")
                    return hierarchy_path
            
            # 네비게이션 메뉴에서 찾지 못한 경우 URL 패턴 기반 추정
            url_based_path = self._infer_path_from_url(current_url)
            if url_based_path != "unknown":
                logger.debug(f"🔍 URL 패턴 기반 브레드크럼 추정: {url_based_path} for {current_url}")
                return url_based_path
            
            return "unknown"
            
        except Exception as e:
            logger.debug(f"메뉴 계층 추출 중 오류: {e}")
            return "unknown"
    
    #1.네비게이션 요소에서 ul/li 계층 구조 분석.
    def _extract_hierarchy_from_nav(self, nav_element, current_url: str) -> str:
        """네비게이션 요소에서 ul/li 계층 구조 분석 (무제한 깊이 재귀)"""
        try:
            # 최상위 메뉴 항목들 찾기
            top_items = nav_element.find_all('li', recursive=False)
            if not top_items:
                # li가 직접적으로 없으면 ul 하위에서 찾기
                top_ul = nav_element.find('ul')
                if top_ul:
                    top_items = top_ul.find_all('li', recursive=False)
            
            for top_item in top_items:
                top_link = top_item.find('a')
                if not top_link:
                    continue
                
                top_text = top_link.get_text().strip()
                top_href = top_link.get('href', '')
                
                # 현재 페이지가 최상위 메뉴 항목인지 확인
                if self._is_same_page(top_href, current_url):
                    return top_text
                
                # 하위 메뉴들에서 재귀적으로 탐색
                sub_menus = top_item.find_all('ul')
                for sub_menu in sub_menus:
                    result = self._check_breadcrumb_hierarchy_recursive(sub_menu, current_url, top_text)
                    if result != "unknown":
                        return result
            
            return "unknown"
            
        except Exception as e:
            logger.debug(f"네비게이션 계층 분석 중 오류: {e}")
            return "unknown"
    
    #1.1 재귀적으로 모든 깊이의 메뉴 계층 탐색
    def _check_breadcrumb_hierarchy_recursive(self, menu_ul, current_url: str, parent_path: str = "", max_depth: int = 10) -> str:
        """재귀적으로 모든 깊이의 메뉴 계층 탐색"""
        if max_depth <= 0:  # 무한 재귀 방지
            logger.debug(f"최대 메뉴 깊이 도달: {parent_path}")
            return "unknown"
        
        try:
            items = menu_ul.find_all('li', recursive=False)
            
            for item in items:
                link = item.find('a')
                if not link:
                    continue
                
                text = link.get_text().strip()
                href = link.get('href', '')
                current_path = f"{parent_path}/{text}" if parent_path else text
                
                # 현재 페이지와 일치하는지 확인
                if self._is_same_page(href, current_url):
                    logger.debug(f"🎯 메뉴 경로 발견: {current_path}")
                    return current_path
                
                # 하위 메뉴들에서 재귀적으로 탐색
                sub_menus = item.find_all('ul')
                for sub_menu in sub_menus:
                    result = self._check_breadcrumb_hierarchy_recursive(
                        sub_menu, current_url, current_path, max_depth - 1
                    )
                    if result != "unknown":
                        return result
            
            return "unknown"
            
        except Exception as e:
            logger.debug(f"재귀 메뉴 탐색 중 오류 (depth: {10-max_depth}): {e}")
            return "unknown"
    


    
    def _is_same_page(self, href: str, current_url: str) -> bool:
        """두 URL이 같은 페이지를 가리키는지 확인"""
        try:
            if not href or href in ['#', 'javascript:', 'mailto:', 'tel:']:
                return False
            
            # 상대 경로를 절대 경로로 변환
            if href.startswith('/'):
                full_href = f"https://{urlparse(current_url).netloc}{href}"
            elif href.startswith('http'):
                full_href = href
            else:
                # 현재 URL 기준 상대 경로 해결
                from urllib.parse import urljoin
                full_href = urljoin(current_url, href)
            
            # URL 정규화하여 비교
            normalized_href = self._normalize_url_for_comparison(full_href)
            normalized_current = self._normalize_url_for_comparison(current_url)
            
            return normalized_href == normalized_current
            
        except Exception as e:
            logger.debug(f"URL 비교 중 오류: {e}")
            return False
    
    def _normalize_url_for_comparison(self, url: str) -> str:
        """URL 비교를 위한 정규화"""
        try:
            from urllib.parse import urlparse, urlunparse
            # URL 공백 제거
            url = url.strip()
            parsed = urlparse(url)
            
            # 쿼리와 프래그먼트 제거, 경로 정규화
            normalized_path = parsed.path.rstrip('/')
            if not normalized_path:
                normalized_path = '/'
            
            return urlunparse((
                parsed.scheme,
                parsed.netloc.lower(),
                normalized_path,
                '',  # params
                '',  # query
                ''   # fragment
            ))
            
        except Exception:
            return url.lower()
    
    def _infer_path_from_url(self, url: str) -> str:
        """URL 패턴에서 논리적 경로 추정 (개선된 버전)"""
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p and p != 'index.do']
            
            # 쿼리 파라미터 분석
            query_params = parse_qs(parsed.query)
            
            # URL 패턴 매핑
            path_mappings = {
                'notice': '공지사항',
                'news': '소식',
                'intro': '소개',
                'about': '소개'
            }
            
            # 경로 부분에서 매핑 확인
            for part in path_parts:
                clean_part = re.sub(r'\.(do|html|htm|jsp|php)$', '', part.lower())
                if clean_part in path_mappings:
                    return path_mappings[clean_part]
            
            # 특정 패턴 분석
            url_lower = url.lower()

            # 다운로드 관련 패턴
            if any(pattern in url_lower for pattern in ['download', 'filedown', 'getfile']):
                return '첨부파일/다운로드'
            
            return "unknown"
            
        except Exception as e:
            logger.debug(f"URL 패턴 추정 중 오류: {e}")
            return "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """노드를 딕셔너리로 변환 (JSON 구조)"""
        # breadcrumb 처리: page_title 사용, unknown은 경로미상으로 표시
        breadcrumb = self.breadcrumb
        if self.depth == 0:  # Root 노드
            # Root 노드의 경우 page_title이 있으면 사용, 없으면 "홈"
            if self.page_title and self.page_title != "제목없음":
                clean_title = self.page_title.strip()
                if ' - ' in clean_title:
                    clean_title = clean_title.split(' - ')[0].strip()
                breadcrumb = clean_title
            else:
                breadcrumb = "홈"
        elif not breadcrumb or breadcrumb == "unknown":
            # 문서 파일인 경우 특별 처리
            if self.is_document:
                if self.parent and self.parent.breadcrumb and self.parent.breadcrumb not in ["unknown", "홈"]:
                    breadcrumb = f"{self.parent.breadcrumb}/첨부파일"
                else:
                    breadcrumb = "첨부파일"
            else:
                # 일반 페이지의 경우 부모 노드의 경로를 기반으로 추정 시도
                if self.parent and self.parent.breadcrumb and self.parent.breadcrumb not in ["unknown", "홈"]:
                    # URL에서 의미있는 부분 추출하여 부모 경로에 추가
                    url_segment = self._extract_meaningful_url_segment()
                    if url_segment:
                        breadcrumb = f"{self.parent.breadcrumb}/{url_segment}"
                    else:
                        breadcrumb = f"{self.parent.breadcrumb}/하위페이지"
                else:
                    breadcrumb = "경로미상"
        
        return {
            "url": self.url,
            "depth": self.depth,
            "page_title": self.page_title if self.page_title else "제목없음",
            "breadcrumb": breadcrumb,
            "is_document": self.is_document,
            "children_count": len(self.children),
            "children": [child.to_dict() for child in self.children] if self.children else [],

        }

class ScopeLimitedCrawler:
    def __init__(self, max_pages: int = 100000, delay: float = 1.0, timeout: int = 20, use_requests: bool = True, max_depth: int = 10, max_pagination_pages: int = 30):
        """크롤러 초기화.
        
        Args:
            max_pages: 크롤링할 최대 페이지 수
            delay: 요청 간 지연 시간(초)
            timeout: 페이지 로딩 시간 제한(초)
            use_requests: 간단한 페이지는 requests 사용, JS가 많은 페이지는 selenium 사용
            max_depth: 최대 깊이 제한
            max_pagination_pages: 페이지네이션에서 크롤링할 최대 페이지 수
        """
        # 통합된 스레드 안전성을 위한 RLock 사용
        self.url_lock = threading.RLock()
        
        # URL 관리를 위한 자료구조 (스레드 안전)
        self.visited_urls: Set[str] = set()  # 방문한 URL 집합
        self.excluded_urls: Set[str] = set()  # 제외된 URL 집합
        self.all_page_urls: Set[str] = set() # 모든 페이지 URL
        self.all_doc_urls: Set[str] = set()  # 모든 문서 URL
        
        # URL 정규화 캐시
        self.normalization_cache = URLNormalizationCache()
        
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

        # DFS를 위한 새로운 속성들
        self.max_depth = max_depth
        self.max_pagination_pages = max_pagination_pages  # 페이지네이션 최대 페이지 수 제한
        self.pagination_urls_count = 0  # 전역 페이지네이션 URL 카운터
        self.url_tree: Optional[URLTreeNode] = None  # URL 트리 루트
        self.url_to_node: Dict[str, URLTreeNode] = {}  # URL -> 노드 매핑
        self.visit_order: List[str] = []  # 방문 순서 기록
        
        # 컨텍스트 인식 DFS를 위한 속성들
        self.global_navigation_map: Dict[str, Any] = {}  # 전역 네비게이션 구조
        self.page_contexts: Dict[str, Dict[str, Any]] = {}  # 페이지별 컨텍스트
        self.used_breadcrumbs: Set[str] = set()  # 사용된 브레드크럼 경로들
        
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
        
        # URL 공백 제거 및 정리
        url = url.strip()
        
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
        
        # 파일 확장자 확인하여 제외 (캐시에 저장하지 않음)
        if any(path.lower().endswith(ext) for ext in EXCLUDE_EXTENSIONS):
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
        """URL이 정의된 크롤링 범위 내에 있는지 확인 (모든 패턴 포함 필수)"""
        try:
            # URL 공백 제거
            url = url.strip()
            parsed = urlparse(url)
            
            # 도메인 확인 - 기본 도메인과 정확히 일치하거나 www 변형만 허용
            current_domain = parsed.netloc.lower()
            base_domain_lower = self.base_domain.lower()
            
            # www 제거한 도메인으로 비교
            current_domain_no_www = current_domain.replace('www.', '', 1) if current_domain.startswith('www.') else current_domain
            base_domain_no_www = base_domain_lower.replace('www.', '', 1) if base_domain_lower.startswith('www.') else base_domain_lower
            
            # 기본 도메인과 일치하지 않으면 제외 (www 변형 허용)
            if current_domain_no_www != base_domain_no_www:
                return False
            
            # scope_patterns가 비어있거나 빈 문자열만 있으면 도메인 전체 허용
            if not self.scope_patterns or (len(self.scope_patterns) == 1 and self.scope_patterns[0] == ''):
                return True
            
            # URL을 소문자로 변환하여 패턴 매칭
            url_lower = url.lower()
            url_path = parsed.path.lower()
            url_query = parsed.query.lower()
            
            # 🎯 NEW: 모든 패턴이 URL에 포함되어야 함 (AND 조건)
            matched_patterns = []
            
            for pattern in self.scope_patterns:
                pattern_lower = pattern.lower()
                
                # 패턴이 URL의 어디든 포함되면 매칭
                if (pattern_lower in url_path or 
                    pattern_lower in url_query or 
                    pattern_lower in url_lower):
                    matched_patterns.append(pattern)
            
            # 🎯 모든 패턴이 매칭되어야 범위 내로 판단
            is_all_matched = len(matched_patterns) == len(self.scope_patterns)
            
            if is_all_matched:
                logger.debug(f"URL이 범위 내 (모든 패턴 매칭): {url}")
                logger.debug(f"필요 패턴: {self.scope_patterns}")
                logger.debug(f"매칭된 패턴: {matched_patterns}")
                return True
            else:
                logger.debug(f"URL이 범위 밖 (일부 패턴만 매칭): {url}")
                logger.debug(f"필요 패턴: {self.scope_patterns}")
                logger.debug(f"매칭된 패턴: {matched_patterns}")
                logger.debug(f"누락된 패턴: {set(self.scope_patterns) - set(matched_patterns)}")
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
            
            # rssList.do로 끝나는 URL 제외
            if lower_url.endswith('rsslist.do'):
                logger.debug(f"rssList.do 패턴으로 URL 제외: {url}")
                self.excluded_urls.add(url)
                return True
            
            # 제외 패턴 확인
            for pattern in EXCLUDE_PATTERNS:
                if pattern in lower_url:
                    logger.debug(f"제외 패턴 '{pattern}' 매칭으로 URL 제외: {url}")
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
        
        # 제외 패턴 확인 (단, API 기반 파일 다운로드는 예외 처리)
        for pattern in EXCLUDE_PATTERNS:
            if pattern in lower_url:
                # API 경로에서 파일 다운로드 패턴이 있으면 예외 처리
                if pattern == '/api/' and any(file_pattern in lower_url for file_pattern in ['/file', '/download', '/attach']):
                    continue  # API 파일 다운로드는 제외하지 않음
                return False
        
        # 1. 문서 파일 확장자 확인 (DOC_EXTENSIONS에 해당하는 것만)
        for ext in DOC_EXTENSIONS:
            if lower_url.endswith(ext):
                return True
        
        # 2. 명확한 문서 다운로드 패턴 확인 (.do 파일들 최우선)
        # 🔥 명확한 다운로드 패턴들은 항상 문서로 분류
        for pattern in EXPLICIT_DOWNLOAD_PATTERNS:
            if pattern in lower_url:
                return True
        
        # 3. 일반적인 다운로드 패턴 확인 (origin 방식 적용)
        for pattern in DOWNLOAD_PATTERNS:
            if pattern in lower_url:
                # 명확히 제외해야 할 패턴들 확인
                exclude_keywords = ['software', 'program', 'app', 'installer', 'setup']
                if not any(keyword in lower_url for keyword in exclude_keywords):
                    # download.do와 fileDown.do는 항상 문서로 분류 (origin과 동일)
                    if pattern in ['/download.do', 'download.do', 'fileDown.do']:
                        return True
                    # 게시판이나 첨부파일 관련 경로인지 확인
                    elif (any(keyword in lower_url for keyword in ['/bbs/', '/board/', '/attach', '/file', '/document']) or
                        not any(keyword in lower_url for keyword in ['software', 'media', 'image', 'video'])):
                        return True
        
        # 4. URL 쿼리 파라미터에서 파일 관련 정보 확인 (개선)
        if '?' in href:
            query_part = href.split('?', 1)[1]
            # 파일 관련 파라미터들
            file_params = ['file', 'filename', 'attach', 'download', 'doc', 'document']
            if any(param in query_part.lower() for param in file_params):
                return True
            
            # 게시판 첨부파일 패턴 (한국 사이트 특화)
            korean_patterns = ['첨부', '파일', '자료', '문서']
            if any(pattern in query_part for pattern in korean_patterns):
                return True
        
        return False

    def add_url_atomically(self, url: str, url_set: Set[str]) -> bool:
        """URL을 원자적으로 집합에 추가 (중복 체크 포함)"""
        with self.url_lock:
            if url not in url_set:
                url_set.add(url)
                return True
            return False

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> Tuple[Set[str], Set[str], Set[str], Set[str]]:
        """페이지에서 링크를 구분하여 추출: (네비게이션 링크, 콘텐츠 링크, 문서 링크, 메뉴 정보)"""
        nav_links = set()      # 네비게이션/메뉴 링크
        content_links = set()  # 콘텐츠 영역 링크
        doc_links = set()      # 문서 파일 링크
        menu_info = set()      # 메뉴 구조 정보
        
        try:
            # 🆕 1. ul/li 계층 구조를 고려한 네비게이션 링크 추출 (우선 처리)
            hierarchical_nav_links, hierarchical_menu_info = self._extract_hierarchical_navigation_links(soup, base_url)
            nav_links.update(hierarchical_nav_links)
            menu_info.update(hierarchical_menu_info)
            
            # 2. 일반 링크 추출 - origin 방식 통합 (계층 구조에서 이미 처리된 링크는 제외)
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
                
                # 이미 계층 구조에서 처리된 네비게이션 링크는 건너뛰기
                if normalized_url in nav_links:
                    continue
                
                # 문서 파일인지 확인 - origin 방식 적용
                is_doc = False
                lower_url = normalized_url.lower()

                # 1. 확장자 기반 문서 파일 확인
                for ext in DOC_EXTENSIONS:
                    if lower_url.endswith(ext):
                        doc_links.add(normalized_url)
                        is_doc = True
                        break
                
                # 2. 선별적 다운로드 패턴 확인 (게시판 첨부파일 등) - origin 로직 복사
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
                
                # 범위 확인 및 네비게이션/콘텐츠 분류
                if not is_doc and self.is_in_scope(normalized_url):
                    # 네비게이션 링크 확인
                    link_text = anchor.get_text().strip()
                    if self._is_valid_navigation_link(href, link_text):
                        nav_links.add(normalized_url)
                        # 메뉴 구조 정보 저장
                        menu_info.add(f"general:{normalized_url}:{link_text}")
                    else:
                        content_links.add(normalized_url)

            # 2. 메뉴 및 네비게이션 링크 특별 처리 - origin 방식 추가
            nav_selectors = [
                'nav a', '.nav a', '.navigation a', '.menu a', '.gnb a', '.lnb a',
                '.main-menu a', '.sub-menu a', '.sidebar a', '.footer a',
                '[class*="menu"] a', '[class*="nav"] a', '[id*="menu"] a', '[id*="nav"] a'
            ]
            
            for selector in nav_selectors:
                nav_elements = soup.select(selector)
                for link in nav_elements:
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
                                
                                # 문서인지 확인
                                if self.is_valid_file_url(href, base_url):
                                    doc_links.add(normalized_url)
                                else:
                                    nav_links.add(normalized_url)
                                    link_text = link.get_text().strip()
                                    menu_info.add(f"nav:{normalized_url}:{link_text}")

            # 3. 첨부파일 추가 처리
            attachment_links = self.extract_attachments(soup, base_url)
            doc_links.update(attachment_links)
            
            logger.debug(f"링크 추출 완료 - 네비게이션: {len(nav_links)}개, 콘텐츠: {len(content_links)}개, 문서: {len(doc_links)}개")
            return nav_links, content_links, doc_links, menu_info
            
        except Exception as e:
            logger.error(f"링크 추출 중 오류 발생: {e}")
            return set(), set(), set(), set()
    
    def _is_valid_navigation_link(self, href: str, link_text: str) -> bool:
        """네비게이션 링크의 유효성 검사"""
        if (not href or href == '#' or 
            href.startswith(('javascript:', 'mailto:', 'tel:')) or
            href.startswith('#')):
            return False
        
        # 짧은 텍스트는 메뉴 항목일 가능성이 높음
        return len(link_text) <= 20
    
    def _build_full_url(self, href: str, base_url: str) -> str:
        """상대/절대 URL을 절대 URL로 변환"""
        if href.startswith('/'):
            return f"https://{self.base_domain}{href}"
        else:
            return urljoin(base_url, href)
    
    def _should_include_link(self, normalized_url: str) -> bool:
        """링크 포함 여부 검사"""
        return (normalized_url and 
                not self.should_exclude_url(normalized_url) and 
                self.is_in_scope(normalized_url))
    
    def _extract_hierarchical_navigation_links(self, soup: BeautifulSoup, base_url: str) -> Tuple[Set[str], Set[str]]:
        """ul/li 계층 구조를 고려한 네비게이션 링크 추출"""
        nav_links = set()
        menu_info = set()
        
        try:
            # 네비게이션 관련 ul 요소들 찾기
            nav_ul_selectors = [
                'nav ul', '.nav ul', '.navigation ul', '.menu ul', 
                '.gnb ul', '.lnb ul', '.main-menu ul', '.sub-menu ul',
                'ul.flex', 'ul.pageNavigation', 'ul[class*="menu"]', 
                'ul[class*="nav"]', 'ul[id*="menu"]', 'ul[id*="nav"]'
            ]
            
            processed_uls = set()  # 중복 처리 방지
            
            for selector in nav_ul_selectors:
                ul_elements = soup.select(selector)
                
                for ul in ul_elements:
                    # 이미 처리된 ul 요소는 건너뛰기
                    ul_id = id(ul)
                    if ul_id in processed_uls:
                        continue
                    processed_uls.add(ul_id)
                    
                    # ul/li 계층 구조 분석
                    extracted_links, extracted_menu_info = self._analyze_ul_li_hierarchy(ul, base_url, depth=0)
                    nav_links.update(extracted_links)
                    menu_info.update(extracted_menu_info)
            
            logger.debug(f"🏗️ 계층 구조 기반 네비게이션 링크 추출: {len(nav_links)}개")
            return nav_links, menu_info
            
        except Exception as e:
            logger.error(f"계층 구조 네비게이션 링크 추출 중 오류: {e}")
            return set(), set()
    
    def _analyze_ul_li_hierarchy(self, ul_element, base_url: str, depth: int = 0, parent_path: str = "") -> Tuple[Set[str], Set[str]]:
        """ul 요소의 li 계층 구조를 재귀적으로 분석"""
        nav_links = set()
        menu_info = set()
        
        try:
            # 최대 깊이 제한 (무한 재귀 방지)
            if depth > 5:
                return nav_links, menu_info
            
            # 직접적인 li 자식들만 처리 (recursive=False)
            direct_li_children = ul_element.find_all('li', recursive=False)
            
            for li in direct_li_children:
                # li 내의 직접적인 a 태그 찾기
                direct_link = li.find('a', recursive=False)
                
                if direct_link and direct_link.has_attr('href'):
                    href = direct_link['href']
                    link_text = direct_link.get_text().strip()
                    
                    # 유효한 링크인지 확인
                    if (href and href != '#' and 
                        not href.startswith(('javascript:', 'mailto:', 'tel:'))):
                        
                        # 절대 URL 생성
                        if href.startswith('/'):
                            full_url = f"https://{self.base_domain}{href}"
                        else:
                            full_url = urljoin(base_url, href)
                        
                        # URL 정규화
                        normalized_url = self.normalize_url(full_url)
                        
                        if (normalized_url and 
                            not self.should_exclude_url(normalized_url) and 
                            self.is_in_scope(normalized_url)):
                            
                            nav_links.add(normalized_url)
                            
                            # 계층 경로 구성
                            current_path = f"{parent_path}/{link_text}" if parent_path else link_text
                            menu_info.add(f"hierarchical:{normalized_url}:{current_path}:depth_{depth}")
                            
                            logger.debug(f"🔗 계층 링크 발견 (깊이 {depth}): {current_path} → {normalized_url}")
                
                # 하위 ul 요소들 재귀 처리
                child_uls = li.find_all('ul', recursive=False)  # 직접적인 ul 자식들만
                
                for child_ul in child_uls:
                    # 현재 li의 텍스트를 부모 경로로 사용
                    current_li_text = ""
                    if direct_link:
                        current_li_text = direct_link.get_text().strip()
                    else:
                        # a 태그가 없는 경우 li의 직접 텍스트 사용
                        li_texts = []
                        for text in li.find_all(text=True, recursive=False):
                            clean_text = text.strip()
                            if clean_text:
                                li_texts.append(clean_text)
                        current_li_text = ' '.join(li_texts) if li_texts else f"메뉴{depth}"
                    
                    child_parent_path = f"{parent_path}/{current_li_text}" if parent_path else current_li_text
                    
                    # 재귀 호출
                    child_links, child_menu_info = self._analyze_ul_li_hierarchy(
                        child_ul, base_url, depth + 1, child_parent_path
                    )
                    
                    nav_links.update(child_links)
                    menu_info.update(child_menu_info)
            
            return nav_links, menu_info
            
        except Exception as e:
            logger.error(f"ul/li 계층 분석 중 오류 (깊이 {depth}): {e}")
            return nav_links, menu_info

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
            
            # 3. DOWNLOAD_PATTERNS를 포함하는 모든 링크 직접 검색 - origin 방식 적용
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

    def detect_pagination(self, soup: BeautifulSoup) -> Tuple[bool, Optional[Any]]:
        """페이지에서 페이지네이션 요소 감지 (Origin 스타일)"""
        try:
            for selector in PAGINATION_SELECTORS:
                elements = soup.select(selector)
                if elements:
                    return True, elements[0]
                    
            return False, None
        except Exception as e:
            logger.error(f"BeautifulSoup으로 페이지네이션 감지 중 오류 발생: {e}")
            return False, None

    def handle_pagination(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """페이지네이션을 처리하여 모든 페이지 URL 반환 (Origin에서 이식)"""
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
                            logger.debug(f"'더보기' 링크 발견: {normalized_url}")
            return pagination_urls
        
        # 2. 페이지 URL 패턴과 마지막 페이지 번호 파악
        url_pattern, last_page = self._extract_pagination_pattern(soup, current_url, pagination_element)
        
        # 페이지 수를 25로 제한
        last_page = min(last_page, 25)
        
        logger.debug(f"URL 패턴: {url_pattern}, 마지막 페이지: {last_page}")
        
        # 3. 직접 페이지 링크 추가 (전역 페이지 수 제한 적용)
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
                                # 전역 페이지네이션 수 제한 체크
                                if self.pagination_urls_count >= self.max_pagination_pages:
                                    logger.debug(f"전역 페이지네이션 제한 ({self.max_pagination_pages}페이지) 도달, 추가 중단")
                                    break
                                pagination_urls.append(normalized_url)
                                self.pagination_urls_count += 1
                                logger.debug(f"직접 페이지네이션 링크 추가 (전역: {self.pagination_urls_count}/{self.max_pagination_pages}): {normalized_url}")
        
        # 4. URL 패턴이 있고 마지막 페이지 번호가 있는 경우, 모든 페이지 URL 생성 (전역 제한 적용)
        if url_pattern and last_page > 0:
            for page_num in range(1, min(last_page + 1, self.max_pagination_pages + 1)):  # 설정된 최대 페이지로 제한
                # 전역 페이지네이션 수 제한 체크
                if self.pagination_urls_count >= self.max_pagination_pages:
                    logger.debug(f"전역 페이지네이션 제한 ({self.max_pagination_pages}페이지) 도달, 패턴 기반 URL 생성 중단")
                    break
                    
                page_url = url_pattern.replace('{page}', str(page_num))
                normalized_url = self.normalize_url(page_url)
                if normalized_url not in pagination_urls and normalized_url != current_url:
                    pagination_urls.append(normalized_url)
                    self.pagination_urls_count += 1
                    logger.debug(f"패턴 기반 페이지네이션 URL 추가 (전역: {self.pagination_urls_count}/{self.max_pagination_pages}): {normalized_url}")
        
        # 페이지네이션 정보 로깅
        if pagination_urls:
            logger.debug(f"페이지네이션 발견: {len(pagination_urls)}개 페이지")
        
        return pagination_urls

    def _is_over_pagination_limit(self, url: str) -> bool:
        """URL이 페이지네이션 파라미터를 포함하고 그 값이 제한을 초과하는지 여부를 반환한다.

        - 지원 키: page, pageNo, pageIndex, p, pg
        - 경로 패턴: /page/<number>
        """
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            query_dict = parse_qs(parsed.query)
            page_keys = ["page", "pageNo", "pageIndex", "p", "pg"]
            for key in page_keys:
                if key in query_dict and query_dict[key]:
                    value = query_dict[key][0]
                    if value.isdigit() and int(value) > self.max_pagination_pages:
                        return True
            # 경로 기반 패턴 확인 (/page/123)
            path = parsed.path or ""
            match = re.search(r"/(?:p|page)/(\d+)", path, re.IGNORECASE)
            if match and int(match.group(1)) > self.max_pagination_pages:
                return True
            return False
        except Exception:
            return False

    def _extract_pagination_pattern(self, soup: BeautifulSoup, current_url: str, pagination_element) -> Tuple[str, int]:
        """페이지네이션 URL 패턴과 마지막 페이지 번호 추출 (Origin에서 이식)"""
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
                logger.debug(f"페이지네이션 패턴 추출: {url_pattern}, 마지막 페이지: {last_page}")
            else:
                logger.debug(f"페이지네이션 패턴 추출 실패, 대체 방법 사용")
                
            return url_pattern, last_page
            
        except Exception as e:
            logger.error(f"페이지네이션 패턴 추출 중 오류: {e}")
            return None, 0

    def _find_url_pattern(self, page_urls: Dict[int, str]) -> str:
        """페이지 URL에서 일관된 패턴 찾기 (Origin에서 이식)"""
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

    def extract_filename_from_download_url(self, url: str) -> str:
        """다운로드 URL에서 실제 파일명 추출"""
        try:
            # HEAD 요청으로 파일명 정보 가져오기 (빠른 방법)
            response = self.session.head(url, timeout=10, allow_redirects=True)
            
            # Content-Disposition 헤더에서 파일명 추출
            content_disposition = response.headers.get('Content-Disposition', '')
            if content_disposition:
                # filename="파일명.확장자" 패턴 찾기
                filename_match = re.search(r'filename[*]?=(?:["\']?)([^"\';\r\n]+)', content_disposition)
                if filename_match:
                    filename = filename_match.group(1).strip()
                    # URL 디코딩 처리
                    try:
                        from urllib.parse import unquote
                        filename = unquote(filename, encoding='utf-8')
                    except:
                        pass
                    logger.debug(f"📄 파일명 추출 성공 (헤더): {filename} from {url}")
                    return filename
            
            # Content-Type에서 파일 형식 추정
            content_type = response.headers.get('Content-Type', '')
            if content_type:
                # MIME 타입에서 확장자 추정
                mime_to_ext = {
                    'application/pdf': '.pdf',
                    'application/msword': '.doc',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                    'application/vnd.hancom.hwp': '.hwp',
                    'text/plain': '.txt',
                    'application/vnd.ms-excel': '.xls',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx'
                }
                
                for mime_type, ext in mime_to_ext.items():
                    if mime_type in content_type:
                        # URL에서 ID 추출하여 파일명 생성
                        url_parts = url.split('/')
                        if len(url_parts) >= 2:
                            doc_id = url_parts[-2]  # download.do 앞의 ID
                            filename = f"문서_{doc_id}{ext}"
                            logger.debug(f"📄 파일명 추출 성공 (MIME): {filename} from {url}")
                            return filename
            
            # 실제 GET 요청으로 내용 확인 (최후 수단)
            try:
                # HTTP 요청 직전 URL 정리
                clean_url = url.strip()
                response = self.session.get(clean_url, timeout=10, stream=True)
                # 응답 헤더 재확인
                content_disposition = response.headers.get('Content-Disposition', '')
                if content_disposition:
                    filename_match = re.search(r'filename[*]?=(?:["\']?)([^"\';\r\n]+)', content_disposition)
                    if filename_match:
                        filename = filename_match.group(1).strip()
                        try:
                            from urllib.parse import unquote
                            filename = unquote(filename, encoding='utf-8')
                        except:
                            pass
                        logger.debug(f"📄 파일명 추출 성공 (GET 헤더): {filename} from {url}")
                        return filename
                
                # 응답 내용에서 파일명 추출 시도 (HTML 페이지인 경우)
                if 'text/html' in response.headers.get('Content-Type', ''):
                    # 일부 내용만 읽어서 파싱
                    content = response.content[:4096].decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # 페이지 제목에서 파일명 추출
                    title_tag = soup.find('title')
                    if title_tag and title_tag.string:
                        title = title_tag.string.strip()
                        return title
                    
                    # 파일 정보가 있는 요소 찾기
                    file_info_selectors = [
                        '.file-name', '.filename', '.document-title', 
                        '[class*="file"]', '[class*="attach"]'
                    ]
                    
                    for selector in file_info_selectors:
                        elements = soup.select(selector)
                        for element in elements:
                            text = element.get_text().strip()
                            if text and len(text) < 100:  # 너무 긴 텍스트는 제외
                                logger.debug(f"📄 파일명 추출 성공 (요소): {text} from {url}")
                                return text
                
            except Exception as e:
                logger.debug(f"GET 요청 중 오류: {e}")
            
            # 모든 방법이 실패한 경우 URL에서 ID 추출
            url_parts = url.split('/')
            if len(url_parts) >= 2:
                doc_id = url_parts[-2]  # download.do 앞의 ID
                filename = f"문서_{doc_id}"
                logger.debug(f"📄 파일명 추출 (기본값): {filename} from {url}")
                return filename
            
            return "다운로드_파일"
            
        except Exception as e:
            logger.debug(f"파일명 추출 중 오류: {e}")
            # URL에서 ID 추출하여 기본 파일명 생성
            try:
                url_parts = url.split('/')
                if len(url_parts) >= 2:
                    doc_id = url_parts[-2]
                    return f"문서_{doc_id}"
            except:
                pass
            return "다운로드_파일"

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
                            
                        # HTTP 요청 직전 URL 정리
                        clean_url = url.strip()
                        response = self.session.get(clean_url, timeout=self.timeout)
                        
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
                        js_required = noscript_content and len(noscript_content.text) > 1000
                        
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
                            # Selenium 요청 직전 URL 정리
                            clean_url = url.strip()
                            self.driver.get(clean_url)
                            
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

    def discover_urls_dfs(self, start_url: str, scope_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """DFS 알고리즘을 사용하여 정의된 범위 내의 모든 URL을 발견함.
        
        Args:
            start_url: 크롤링 시작 URL
            scope_patterns: 크롤링 범위를 제한하는 패턴 목록
            
        Returns:
            발견된 URL과 트리 구조가 포함된 딕셔너리
        """
        start_time = time.time()
        
        # 초기화
        start_url = self.normalize_url(start_url)
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc
        self.start_url = start_url  # 🏠 메인 페이지 식별을 위한 start_url 저장
        
        # 범위 패턴 설정
        if scope_patterns:
            self.scope_patterns = [p.lower() for p in scope_patterns]
            logger.debug(f"수동 설정된 범위 패턴: {self.scope_patterns}")
        else:
            self.scope_patterns = self._auto_extract_scope_patterns(start_url)
            logger.debug(f"자동 추출된 범위 패턴: {self.scope_patterns}")
        
        # 범위 적용 결과 로깅 (DEBUG 레벨로 변경)
        if self.scope_patterns == ['']:
            logger.debug(f"크롤링 범위: {self.base_domain} 도메인 전체")
        else:
            logger.debug(f"크롤링 범위: {self.base_domain} 도메인에서 {self.scope_patterns} 패턴 포함 페이지만")
        
        # 컬렉션 초기화
        self.all_page_urls.clear()
        self.all_doc_urls.clear()
        self.visited_urls.clear()
        self.url_to_node.clear()
        self.visit_order.clear()
        
        # 컨텍스트 인식 DFS를 위한 초기화
        self.global_navigation_map.clear()
        self.page_contexts.clear()
        self.used_breadcrumbs.clear()
        
        # 루트 노드 생성
        self.url_tree = URLTreeNode(start_url, None, 0)
        self.url_to_node[start_url] = self.url_tree
        
        # 파일 저장 설정
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        scope_name = '_'.join(self.scope_patterns) if self.scope_patterns else 'full_domain'
        domain_name = self.base_domain.replace('.', '_')
        domain_dir = os.path.join(BASE_DIR, f"{timestamp}_{domain_name}_{scope_name}_dfs")
        os.makedirs(domain_dir, exist_ok=True)
        
        # 로깅 설정
        log_file = os.path.join(domain_dir, f"crawling_log_dfs_{timestamp}.txt")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        logger.debug(f"DFS 크롤링 시작: {start_url}")
        logger.debug(f"기본 도메인: {self.base_domain}")
        logger.debug(f"범위 패턴: {self.scope_patterns}")
        logger.debug(f"최대 페이지: {self.max_pages}, 최대 깊이: {self.max_depth}")
        
        try:
            # DFS 실행
            self._dfs_crawl(self.url_tree)
            
            # 트리 구조 저장
            tree_file = os.path.join(domain_dir, f"url_tree_{timestamp}.json")
            self._save_tree_structure(tree_file)
            
            # 문서 URL 별도 파일로 저장
            doc_urls_file = os.path.join(domain_dir, f"document_urls_{timestamp}.txt")
            self._save_document_urls(doc_urls_file)
            
            # 페이지 URL 별도 파일로 저장
            page_urls_file = os.path.join(domain_dir, f"page_urls_{timestamp}.txt")
            self._save_page_urls(page_urls_file)
            
            # 통계 생성
            stats = self._generate_tree_statistics()
            
            # 결과 JSON 저장 (필수 정보만 포함)
            json_data = {
                "timestamp": timestamp,
                "execution_time_seconds": time.time() - start_time,
                "base_url": start_url,
                "base_domain": self.base_domain,
                "scope_patterns": self.scope_patterns,
                "total_pages_discovered": len(self.all_page_urls),
                "total_documents_discovered": len(self.all_doc_urls),
                "max_depth": stats["max_depth"],
                "tree_statistics": {
                    "total_nodes": stats["total_nodes"],
                    "nodes_per_depth": stats["nodes_per_depth"],
                    "document_nodes": stats["document_nodes"],
                    "page_nodes": stats["page_nodes"],
                    "page_types": stats["page_types"],
                    "avg_load_time": stats["avg_load_time"]
                },
                "tree_file": tree_file,
                "doc_urls_file": doc_urls_file,
                "page_urls_file": page_urls_file
            }
            
            json_file = os.path.join(domain_dir, f"dfs_results_{timestamp}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"\n✅ DFS 크롤링 완료:")
            logger.info(f"📊 발견된 페이지: {len(self.all_page_urls)}개")
            logger.info(f"📄 발견된 문서: {len(self.all_doc_urls)}개")
            logger.info(f"📏 최대 깊이: {stats['max_depth']}")
            
            # 웹사이트 구조 분석 보고서 출력
            if stats['total_nodes'] > 0:
                logger.info(f"\n{self.generate_structure_report()}")
            
            # 트리 구조 시각화 생성 (단일 그래프만)
            visualization_file = ""
            if SimpleTreeVisualizer and self.url_tree and stats['total_nodes'] > 0:
                try:
                    logger.info("🎨 웹사이트 구조 그래프 생성 중...")
                    visualizer = SimpleTreeVisualizer()
                    
                    # 단일 그래프 파일 생성
                    visualization_file = visualizer.generate_single_graph(
                        self.url_tree, 
                        domain_dir, 
                        f"website_structure_{timestamp}"
                    )
                    
                    if visualization_file:
                        logger.info(f"✅ 그래프 시각화 생성 완료:")
                        logger.info(f"   📊 그래프: {os.path.basename(visualization_file)}")
                        logger.info(f"💡 '{os.path.basename(visualization_file)}' 파일을 열어 트리 구조를 확인하세요!")
                    
                except Exception as e:
                    logger.error(f"시각화 생성 중 오류 발생: {e}")
                    visualization_file = ""
            else:
                if not SimpleTreeVisualizer:
                    logger.warning("SimpleTreeVisualizer를 사용할 수 없어 시각화를 건너뜁니다.")
                elif not self.url_tree:
                    logger.warning("트리 구조가 없어 시각화를 건너뜁니다.")
                elif stats['total_nodes'] == 0:
                    logger.warning("노드가 없어 시각화를 건너뜁니다.")
            
            # 파일 개수 및 완료 메시지 출력 (시각화 완료 후)
            total_files = 5 + (1 if visualization_file else 0)
            logger.info(f"🗂️ 생성된 파일: {total_files}개")
            logger.info(f"   📋 문서 URL 목록: {os.path.basename(doc_urls_file)}")
            logger.info(f"   📄 페이지 URL 목록: {os.path.basename(page_urls_file)}")
            logger.info(f"⚡ 실행 시간: {time.time() - start_time:.1f}초")
            
            # 파일 생성 목록 업데이트
            files_generated = ["url_tree", "dfs_results", "crawling_log", "document_urls", "page_urls"]
            if visualization_file:
                files_generated.append("graph_visualization")
            
            return {
                "json_data": json_data,
                "page_urls": list(self.all_page_urls),
                "doc_urls": list(self.all_doc_urls),
                "tree_structure": self.url_tree.to_dict(),
                "tree_statistics": stats,
                "results_dir": domain_dir,
                "tree_file": tree_file,
                "doc_urls_file": doc_urls_file,
                "page_urls_file": page_urls_file,
                "visualization_file": visualization_file,
                "execution_time": time.time() - start_time,
                "files_generated": files_generated
            }
            
        except Exception as e:
            logger.error(f"DFS 크롤링 실패: {e}")
            return {
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        
        finally:
            # 로그 핸들러 정리
            if 'file_handler' in locals():
                logger.removeHandler(file_handler)
                file_handler.close()
            self.close_driver()
    
    def _dfs_crawl(self, current_node: URLTreeNode) -> None:
        """DFS를 사용하여 재귀적으로 URL 크롤링"""
        # 방문 한도 체크
        if len(self.visited_urls) >= self.max_pages:
            return
        
        # 깊이 제한 체크
        if current_node.depth >= self.max_depth:
            logger.debug(f"최대 깊이 도달: {current_node.url} (깊이: {current_node.depth})")
            return
        
        url = current_node.url
        
        # 이미 방문한 URL 건너뛰기
        if url in self.visited_urls:
            return
        
        # 범위 체크
        if not self.is_in_scope(url) or self.should_exclude_url(url):
            return
        
        # 방문 표시
        self.visited_urls.add(url)
        self.visit_order.append(url)
        current_node.visited_at = datetime.now()
        
        progress = f"[{len(self.visited_urls)}/{self.max_pages}] 깊이 {current_node.depth}"
        logger.info(f"{progress} 방문: {url}")
        
        try:
            # 페이지 로딩 시간 측정 시작
            start_time = time.time()
            
            # 페이지 가져오기
            success, content, current_url = self.fetch_page(url)
            
            # 로딩 시간 기록
            current_node.load_time = time.time() - start_time
            
            if not success:
                logger.warning(f"페이지 가져오기 실패: {url}")
                
                # 문서 파일이 아닌 경우 트리에서 제거
                if not current_node.is_document and not self.is_valid_file_url(url, url):
                    self._remove_failed_node(current_node)
                    logger.debug(f"접근 실패한 일반 페이지 노드 제거: {url}")
                    return
                else:
                    # 문서 파일인 경우 유지하되 적절한 제목과 경로 설정
                    self._handle_failed_document_node(current_node)
                    logger.debug(f"접근 실패한 문서 파일 노드 유지: {url}")
                    return
            
            # URL 업데이트 (리다이렉트 등으로 변경된 경우)
            if current_url != url:
                current_node.url = self.normalize_url(current_url)
                url = current_node.url
            
            # BeautifulSoup 파싱
            if isinstance(content, BeautifulSoup):
                soup = content
                # requests로 가져온 경우 response에서 크기 추정
                # 실제로는 이 정보가 제한적이므로 HTML 길이로 추정
                html_content = str(soup)
                current_node.file_size = len(html_content.encode('utf-8'))
            else:
                self._init_selenium()
                html_content = self.driver.page_source
                soup = BeautifulSoup(html_content, 'html.parser')
                # 파일 크기 측정
                current_node.file_size = len(html_content.encode('utf-8'))
            
            # 페이지 제목 추출 - 게시글 보기 페이지인 경우 특별 처리
            article_title = self._extract_article_title(soup, current_node.url)
            if article_title:
                current_node.page_title = article_title
            else:
                # 일반 페이지는 title 태그 사용
                title_tag = soup.find('title')
                if title_tag:
                    current_node.page_title = title_tag.get_text().strip()
            
            # 웹사이트 구조 분석을 위한 추가 정보 추출
            current_node.page_type = current_node.classify_page_type(soup, self.start_url)
            
            # 컨텍스트 인식 메뉴 계층 경로 설정
            if current_node.parent is None:
                # 루트 노드: page_title 또는 기본값 설정
                if current_node.page_title and current_node.page_title != "제목없음":
                    clean_title = current_node.page_title.strip()
                    if ' - ' in clean_title:
                        clean_title = clean_title.split(' - ')[0].strip()
                    current_node.breadcrumb = clean_title
                else:
                    current_node.breadcrumb = "홈"
                # 전역 네비게이션 맵 초기화
                self._update_global_navigation_map(soup, current_node)
                logger.debug(f"🏠 Root 경로 설정: {current_node.breadcrumb}")
            else:
                # 게시글 보기 페이지인 경우 제목이 이미 추출되었으므로 바로 사용
                if self._is_article_view_page(current_node.url) and self._is_valid_article_title(current_node.page_title):
                    # 게시글인 경우 부모 경로 + 게시글 제목
                    if current_node.parent and current_node.parent.breadcrumb:
                        current_node.breadcrumb = f"{current_node.parent.breadcrumb}/{current_node.page_title}"
                    else:
                        current_node.breadcrumb = current_node.page_title
                else:
                    # 컨텍스트 인식 메뉴 경로 결정
                    current_node.breadcrumb = self._determine_context_aware_breadcrumb(current_node, soup)
            
            # 링크 추출
            nav_links, content_links, doc_links, menu_info = self.extract_links(soup, url)
            current_node.doc_links = list(doc_links)
            current_node.navigation_links = list(nav_links)
            current_node.content_links = list(content_links)
            current_node.link_count = len(nav_links) + len(content_links) + len(doc_links)
            
            # 메뉴 구조 정보 파싱
            for menu_item in menu_info:
                if ':' in menu_item:
                    menu_type, menu_url, menu_text = menu_item.split(':', 2)
                    if menu_url == url:
                        current_node.menu_position = menu_type
                        current_node.is_navigation_node = True
                        current_node.navigation_level = current_node.depth  # 임시, 나중에 정확히 계산
            
            # 현재 URL이 문서인지 확인
            if self.is_valid_file_url(url, url):
                current_node.is_document = True
                self.all_doc_urls.add(url)
                
                # 📄 다운로드 링크인 경우 파일명 추출
                if 'download.do' in url and current_node.page_title in ["제목없음", ""]:
                    filename = self.extract_filename_from_download_url(url)
                    current_node.page_title = filename
                    logger.info(f"📄 현재 페이지 파일명 추출: {filename} from {url}")
                
                logger.debug(f"{progress} 문서 페이지 확인: {url}")
            else:
                # 게시판 목록 페이지가 아닌 경우에만 페이지 URL로 추가
                if not self.is_list_page(url):
                    self.all_page_urls.add(url)
            
            # 문서 URL 추가 (페이지에서 발견된 문서 링크들)
            for doc_url in doc_links:
                normalized_doc_url = self.normalize_url(doc_url)
                if normalized_doc_url and normalized_doc_url not in self.all_doc_urls:
                    self.all_doc_urls.add(normalized_doc_url)
                    logger.debug(f"{progress} 문서 발견: {normalized_doc_url}")
                    
                    # 문서 노드 생성 (통계에 반영되도록)
                    if normalized_doc_url not in self.url_to_node:
                        doc_node = URLTreeNode(normalized_doc_url, current_node, current_node.depth + 1)
                        doc_node.is_document = True
                        doc_node.page_type = "document"
                        doc_node.visited_at = datetime.now()
                        doc_node.file_size = 0  # 외부 파일이므로 크기 미측정
                        
                        # 📄 다운로드 링크에서 파일명 추출
                        if 'download.do' in normalized_doc_url:
                            filename = self.extract_filename_from_download_url(normalized_doc_url)
                            doc_node.page_title = filename
                            logger.info(f"📄 파일명 추출: {filename} from {normalized_doc_url}")
                        else:
                            doc_node.page_title = "다운로드_파일"
                        
                        self.url_to_node[normalized_doc_url] = doc_node
                        current_node.children.append(doc_node)
                        logger.debug(f"문서 노드 생성: {normalized_doc_url} (부모: {url})")
            
            # 페이지네이션 URL 추출 (Origin 스타일 고급 처리)
            pagination_urls = self.handle_pagination(soup, url)
            
            # 우선순위 기반 자식 노드 생성 - 모든 링크 수집하되 중복 제거
            # 1. 모든 링크를 합쳐서 처리 (네비게이션 + 콘텐츠 + 페이지네이션)
            all_child_links = set(nav_links) | set(content_links) | set(pagination_urls)
            
            # 페이지네이션 URL 로깅
            if pagination_urls:
                logger.debug(f"{progress} 페이지네이션 발견: {len(pagination_urls)}개 추가 페이지")
            
            for child_url in all_child_links:
                # 전역 페이지네이션 한도 초과 URL은 어떤 경로에서 오든 스킵
                if self._is_over_pagination_limit(child_url):
                    logger.debug(f"전역 페이지네이션 한도 초과 스킵: {child_url}")
                    continue
                normalized_child = self.normalize_url(child_url)
                
                if (normalized_child and 
                    normalized_child not in self.visited_urls and 
                    normalized_child not in self.url_to_node and
                    self.is_in_scope(normalized_child) and 
                    not self.should_exclude_url(normalized_child)):
                    
                    # 자식 노드 생성
                    child_node = current_node.add_child(normalized_child)
                    
                    # 링크 유형에 따른 속성 설정
                    if child_url in nav_links:
                        child_node.is_navigation_node = True
                        child_node.navigation_level = current_node.navigation_level + 1
                        child_node.logical_parent = current_node
                        current_node.logical_children.append(child_node)
                        logger.debug(f"🧭 네비게이션 자식 노드 추가: {normalized_child} (부모: {url})")
                    elif child_url in pagination_urls:
                        child_node.page_type = "general"  # 페이지네이션도 일반 페이지로 분류
                        child_node.logical_parent = current_node
                        logger.debug(f"📖 페이지네이션 자식 노드 추가: {normalized_child} (부모: {url})")
                    else:
                        logger.debug(f"📄 콘텐츠 자식 노드 추가: {normalized_child} (부모: {url})")
                    
                    self.url_to_node[normalized_child] = child_node
                
                # 이미 존재하는 노드에 대한 관계 설정
                elif normalized_child in self.url_to_node:
                    existing_node = self.url_to_node[normalized_child]
                    
                    # 네비게이션 링크인 경우 논리적 관계 설정
                    if child_url in nav_links:
                        if not existing_node.logical_parent:
                            existing_node.logical_parent = current_node
                            current_node.logical_children.append(existing_node)
                        

                        logger.debug(f"🔗 네비게이션 논리적 관계 설정: {normalized_child} ← {url}")
                    

                    


            # 우선순위 기반 DFS 재귀 호출
            # 1. 네비게이션 자식들 먼저 탐색 (최우선)
            for child in current_node.children:
                if child.is_navigation_node and child.url not in self.visited_urls:
                    time.sleep(self.delay)
                    self._dfs_crawl(child)
                    
                    if len(self.visited_urls) >= self.max_pages:
                        break
            
            # 2. 일반 콘텐츠 자식들 탐색 (나머지 모든 자식들)
            for child in current_node.children:
                if (not child.is_navigation_node and 
                    child.url not in self.visited_urls):
                    time.sleep(self.delay)
                    self._dfs_crawl(child)
                    
                    if len(self.visited_urls) >= self.max_pages:
                        break
            
        except Exception as e:
            logger.error(f"URL 처리 중 오류 발생: {url}, {e}")
            current_node.error_status = f"error: {str(e)[:100]}"
            
            # 문서 파일이 아닌 경우 오류 노드도 제거
            if not current_node.is_document and not self.is_valid_file_url(url, url):
                self._remove_failed_node(current_node)
                logger.debug(f"오류 발생한 일반 페이지 노드 제거: {url}")
            else:
                # 문서 파일인 경우 오류 상태로 유지
                self._handle_failed_document_node(current_node)
                logger.debug(f"오류 발생한 문서 파일 노드 유지: {url}")
    
    def _remove_failed_node(self, failed_node: URLTreeNode) -> None:
        """접근에 실패한 노드를 트리에서 제거"""
        try:
            # 부모 노드의 children 리스트에서 제거
            if failed_node.parent and failed_node in failed_node.parent.children:
                failed_node.parent.children.remove(failed_node)
                logger.debug(f"부모 노드에서 실패 노드 제거: {failed_node.url}")
            
            # url_to_node 매핑에서 제거
            if failed_node.url in self.url_to_node:
                del self.url_to_node[failed_node.url]
                logger.debug(f"URL 매핑에서 실패 노드 제거: {failed_node.url}")
            
            # visited_urls에서도 제거 (재시도 가능하도록)
            if failed_node.url in self.visited_urls:
                self.visited_urls.remove(failed_node.url)
            
            # visit_order에서도 제거
            if failed_node.url in self.visit_order:
                self.visit_order.remove(failed_node.url)
                
        except Exception as e:
            logger.error(f"실패 노드 제거 중 오류: {e}")
    
    def _handle_failed_document_node(self, doc_node: URLTreeNode) -> None:
        """접근에 실패한 문서 노드를 적절히 처리"""
        try:
            # 문서로 표시
            doc_node.is_document = True
            doc_node.page_type = "document"
            
            # 파일명 추출 시도
            if 'download.do' in doc_node.url:
                filename = self.extract_filename_from_download_url(doc_node.url)
                if filename:
                    doc_node.page_title = f"{filename} (접근불가)"
                else:
                    doc_node.page_title = "다운로드_파일 (접근불가)"
            else:
                # URL에서 파일명 추정
                from urllib.parse import urlparse
                parsed = urlparse(doc_node.url)
                path_parts = parsed.path.split('/')
                if path_parts:
                    last_part = path_parts[-1]
                    if '.' in last_part:
                        doc_node.page_title = f"{last_part} (접근불가)"
                    else:
                        doc_node.page_title = "문서파일 (접근불가)"
                else:
                    doc_node.page_title = "문서파일 (접근불가)"
            
            # 부모 기반 메뉴 경로 설정
            if doc_node.parent and doc_node.parent.breadcrumb not in ["unknown", "Root URL"]:
                doc_node.breadcrumb = f"{doc_node.parent.breadcrumb}/첨부파일"
            else:
                doc_node.breadcrumb = "첨부파일"
            
            # 문서 URL 목록에 추가
            self.all_doc_urls.add(doc_node.url)
            
            logger.debug(f"문서 노드 처리 완료: {doc_node.page_title} - {doc_node.breadcrumb}")
            
        except Exception as e:
            logger.error(f"문서 노드 처리 중 오류: {e}")
            # 기본값 설정
            doc_node.page_title = "문서파일 (접근불가)"
            doc_node.breadcrumb = "첨부파일"
    
    def _save_tree_structure(self, tree_file: str) -> None:
        """트리 구조를 JSON 파일로 저장"""
        try:
            tree_data = self.url_tree.to_dict() if self.url_tree else {}
            with open(tree_file, 'w', encoding='utf-8') as f:
                json.dump(tree_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"트리 구조 저장 완료: {tree_file}")
        except Exception as e:
            logger.error(f"트리 구조 저장 실패: {e}")
    
    def _save_document_urls(self, doc_urls_file: str) -> None:
        """문서 URL들을 텍스트 파일로 저장"""
        try:
            # 문서 URL을 정렬하여 저장 (일관성 있는 순서)
            sorted_doc_urls = sorted(list(self.all_doc_urls))
            
            with open(doc_urls_file, 'w', encoding='utf-8') as f:
                for doc_url in sorted_doc_urls:
                    f.write(f"{doc_url}\n")
            
            logger.debug(f"문서 URL 저장 완료: {doc_urls_file} ({len(sorted_doc_urls)}개)")
        except Exception as e:
            logger.error(f"문서 URL 저장 실패: {e}")
    
    def _save_page_urls(self, page_urls_file: str) -> None:
        """문서가 아닌 페이지 URL들을 텍스트 파일로 저장"""
        try:
            # 페이지 URL을 정렬하여 저장 (일관성 있는 순서)
            sorted_page_urls = sorted(list(self.all_page_urls))
            
            with open(page_urls_file, 'w', encoding='utf-8') as f:
                for page_url in sorted_page_urls:
                    f.write(f"{page_url}\n")
            
            logger.debug(f"페이지 URL 저장 완료: {page_urls_file} ({len(sorted_page_urls)}개)")
        except Exception as e:
            logger.error(f"페이지 URL 저장 실패: {e}")
    
    def _generate_tree_statistics(self) -> Dict[str, Any]:
        """트리 통계 생성 (필수 정보만)"""
        if not self.url_tree:
            return {}
        
        stats = {
            "total_nodes": 0,
            "max_depth": 0,
            "nodes_per_depth": {},
            "document_nodes": 0,
            "page_nodes": 0,
            "page_types": {},  # 페이지 타입별 분포
            "avg_load_time": 0.0,
            "total_file_size": 0
        }
        
        load_times = []
        
        def traverse_tree(node: URLTreeNode, depth: int = 0):
            stats["total_nodes"] += 1
            stats["max_depth"] = max(stats["max_depth"], depth)
            
            # 깊이별 노드 수
            if depth not in stats["nodes_per_depth"]:
                stats["nodes_per_depth"][depth] = 0
            stats["nodes_per_depth"][depth] += 1
            
            # 노드 유형별 카운트
            if node.is_document:
                stats["document_nodes"] += 1
            else:
                stats["page_nodes"] += 1
            
            # 페이지 타입별 분포
            if node.page_type:
                if node.page_type not in stats["page_types"]:
                    stats["page_types"][node.page_type] = 0
                stats["page_types"][node.page_type] += 1
            
            # 로딩 시간 수집
            if node.load_time > 0:
                load_times.append(node.load_time)
            
            # 파일 크기 수집
            if node.file_size > 0:
                stats["total_file_size"] += node.file_size
            
            # 자식 노드 처리
            for child in node.children:
                traverse_tree(child, depth + 1)
        
        traverse_tree(self.url_tree)
        
        # 평균 로딩 시간 계산
        if load_times:
            stats["avg_load_time"] = sum(load_times) / len(load_times)
        
        return stats

    
    def print_tree_structure(self, max_depth_display: int = 3) -> str:
        """트리 구조를 텍스트로 출력 (디버깅용)"""
        if not self.url_tree:
            return "트리가 생성되지 않았습니다."
        
        lines = []
        
        def print_node(node: URLTreeNode, prefix: str = "", is_last: bool = True, depth: int = 0):
            if depth > max_depth_display:
                return
            
            # 노드 표시 (개선된 정보 포함)
            connector = "└── " if is_last else "├── "
            
            # 노드 타입과 상태 표시
            node_type = "[DOC]" if node.is_document else f"[{node.page_type.upper()}]" if node.page_type else "[PAGE]"
            
            # 추가 정보 표시
            info_parts = []
            if node.page_title:
                info_parts.append(f"제목: {node.page_title[:30]}...")
            if node.load_time > 0:
                info_parts.append(f"로딩: {node.load_time:.1f}s")
            if node.link_count > 0:
                info_parts.append(f"링크: {node.link_count}개")


            
            info_str = f" ({', '.join(info_parts)})" if info_parts else ""
            
            lines.append(f"{prefix}{connector}{node_type} {node.url}{info_str}")
            
            # 메뉴 계층 경로 표시
            if node.breadcrumb != "unknown" and depth <= max_depth_display:
                lines.append(f"{prefix}{'    ' if is_last else '│   '}📍 메뉴경로: {node.breadcrumb}")
            
            # 자식 노드 표시
            if depth < max_depth_display:
                child_prefix = prefix + ("    " if is_last else "│   ")
                for i, child in enumerate(node.children):
                    is_last_child = (i == len(node.children) - 1)
                    print_node(child, child_prefix, is_last_child, depth + 1)
        
        print_node(self.url_tree)
        return "\n".join(lines)
    
    def generate_structure_report(self) -> str:
        """웹사이트 구조 분석 보고서 생성"""
        if not self.url_tree:
            return "트리가 생성되지 않았습니다."
        
        stats = self._generate_tree_statistics()
        report_lines = []
        
        # 기본 정보
        report_lines.append("=" * 50)
        report_lines.append("웹사이트 구조 분석 보고서")
        report_lines.append("=" * 50)
        report_lines.append("기본 통계:")
        report_lines.append(f"  • 총 페이지 수: {stats['total_nodes']:,}개")
        report_lines.append(f"  • 최대 깊이: {stats['max_depth']}레벨")
        report_lines.append(f"  • 문서 파일: {stats['document_nodes']:,}개")
        report_lines.append(f"  • 일반 페이지: {stats['page_nodes']:,}개")


        report_lines.append("")
        
        # 페이지 타입 분포
        if stats['page_types']:
            report_lines.append("페이지 타입 분포:")
            for page_type, count in sorted(stats['page_types'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / stats['total_nodes']) * 100
                report_lines.append(f"  • {page_type}: {count:,}개 ({percentage:.1f}%)")
            report_lines.append("")
        
        # 성능 지표
        report_lines.append("성능 지표:")
        report_lines.append(f"  • 평균 로딩 시간: {stats['avg_load_time']:.2f}초")
        report_lines.append(f"  • 총 데이터 크기: {stats['total_file_size'] / 1024 / 1024:.1f}MB")
        report_lines.append("")
        

        
        # 가장 많이 참조된 페이지들 (비활성화됨)
        # if stats['most_referenced_pages']:
        #     report_lines.append("가장 많이 참조된 페이지들:")
        #     for i, (url, count) in enumerate(stats['most_referenced_pages'][:5], 1):
        #         report_lines.append(f"  {i}. {url} ({count}회 참조)")
        #     report_lines.append("")
        
        # 깊이별 분포
        report_lines.append("깊이별 노드 분포:")
        for depth, count in sorted(stats['nodes_per_depth'].items()):
            percentage = (count / stats['total_nodes']) * 100
            bar = "█" * min(int(percentage), 30)
            report_lines.append(f"  깊이 {depth}: {count:,}개 ({percentage:.1f}%) {bar}")
        report_lines.append("")
        
        # DFS 사이트맵 및 연관관계 분석
        if stats.get('total_menu_contexts', 0) > 0:
            report_lines.append("DFS 사이트맵 연관관계 분석:")
            report_lines.append(f"  • 총 메뉴 맥락: {stats.get('total_menu_contexts', 0):,}개")
            report_lines.append(f"  • 최대 메뉴 깊이: {stats.get('max_menu_depth', 0)}레벨")

            report_lines.append("  • 긴 경로 우선으로 문서 문맥 보존")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def generate_derived_files(self, output_dir: str, file_types: list = None) -> Dict[str, str]:
        """필요시 파생 파일들을 생성 (선택적)"""
        if not self.url_tree:
            return {"error": "트리가 생성되지 않았습니다."}
        
        if file_types is None:
            file_types = ['csv', 'report', 'tree_viz']
        
        exports = {}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # CSV 형태의 플랫 데이터
            if 'csv' in file_types:
                csv_file = os.path.join(output_dir, f"pages_data_{timestamp}.csv")
                self._export_to_csv(csv_file)
                exports['csv'] = csv_file
                logger.debug(f"CSV 파일 생성: {csv_file}")
            
            # 상세 보고서 텍스트 파일
            if 'report' in file_types:
                report_file = os.path.join(output_dir, f"structure_report_{timestamp}.txt")
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(self.generate_structure_report())
                exports['report'] = report_file
                logger.debug(f"구조 리포트 생성: {report_file}")
            
            # 트리 구조 시각화 텍스트
            if 'tree_viz' in file_types:
                tree_file = os.path.join(output_dir, f"tree_structure_{timestamp}.txt")
                with open(tree_file, 'w', encoding='utf-8') as f:
                    f.write(self.print_tree_structure(max_depth_display=5))
                exports['tree_viz'] = tree_file
                logger.debug(f"트리 시각화 생성: {tree_file}")
            
            # 통계 요약 JSON (dfs_results.json에 이미 포함되어 있지만 별도 파일이 필요한 경우)
            if 'statistics' in file_types:
                stats_file = os.path.join(output_dir, f"statistics_{timestamp}.json")
                stats = self._generate_tree_statistics()
                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)
                exports['statistics'] = stats_file
                logger.debug(f"통계 파일 생성: {stats_file}")
            
            logger.debug(f"파생 파일 생성 완료: {len(exports)}개 파일")
            return exports
            
        except Exception as e:
            logger.error(f"파생 파일 생성 실패: {e}")
            return {"error": str(e)}
    
    def _export_to_csv(self, csv_file: str) -> None:
        """페이지 데이터를 CSV 형태로 내보내기"""
        try:
            import csv
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 헤더 작성
                headers = [
                    'URL', '깊이', '페이지타입', '제목', '네비게이션경로', 
                    '자식수', '링크수', '로딩시간', '파일크기', 
                    '방문시간', '문서여부'
                ]
                writer.writerow(headers)
                
                # 데이터 작성
                def write_node_data(node: URLTreeNode):
                    row = [
                        node.url,
                        node.depth,
                        node.page_type,
                        node.page_title,
                        node.breadcrumb if node.breadcrumb != "unknown" else '',
                        len(node.children),
                        node.link_count,
                        f"{node.load_time:.2f}" if node.load_time > 0 else '',
                        node.file_size,
                        node.visited_at.isoformat() if node.visited_at else '',
                        'Yes' if node.is_document else 'No'
                    ]
                    writer.writerow(row)
                    
                    for child in node.children:
                        write_node_data(child)
                
                if self.url_tree:
                    write_node_data(self.url_tree)
                    
        except Exception as e:
            logger.error(f"CSV 내보내기 실패: {e}")



    def _auto_extract_scope_patterns(self, start_url: str) -> List[str]:
        """URL 경로에서 의미있는 세그먼트들을 자동 추출"""
        try:
            parsed_url = urlparse(start_url)
            path_parts = [part for part in parsed_url.path.split('/') if part]
        
            # 제외할 일반적인 용어들만 상수로 정의 (최소한)
            GENERIC_TERMS = [
                'index.do', 'index.html', 'index.htm', 'index.jsp', 'index.php', 'index.asp',
                'main.do', 'main.html', 'main.jsp', 'main.php',
                'home.do', 'home.html', 'home.jsp', 'home.php',
                'list.do', 'list.html', 'view.do', 'view.html',
                'page.do', 'page.html', 'default.do', 'default.html',
                'web', 'www', 'home', 'main', 'index', 'page', 'view', 'list', 'default', 'sites'
            ]
            
            # 순수 경로 세그먼트 추출
            meaningful_segments = []
            
            for part in path_parts:
                # 소문자 변환
                clean_part = part.lower()
                
                # 파일 확장자 제거 (.do, .html 등)
                clean_part = re.sub(r'\.(do|html|htm|jsp|php|asp|aspx)$', '', clean_part)
                
                # 일반적인 용어가 아니고, 의미있는 길이면 추가
                if (clean_part not in GENERIC_TERMS and 
                    len(clean_part) > 1 and 
                    clean_part.isalnum()):
                    meaningful_segments.append(clean_part)
            
            # 결과 검증
            if not meaningful_segments:
                logger.debug("의미있는 경로 세그먼트가 없어 도메인 전체를 범위로 설정")
                return ['']
            
            logger.debug(f"자동 추출된 범위 패턴: {meaningful_segments}")
            logger.debug(f"원본 경로: {parsed_url.path}")
            logger.debug(f"정제된 세그먼트: {' → '.join(meaningful_segments)}")
            
            return meaningful_segments
            
        except Exception as e:
            logger.error(f"자동 패턴 추출 실패: {e}")
            return ['']  # 실패 시 전체 도메인


    

    
    def _determine_context_aware_breadcrumb(self, current_node: URLTreeNode, soup: BeautifulSoup) -> str:
        """컨텍스트 인식 브레드크럼 경로 결정 - 다중 전략 사용"""
        try:
            # 페이지 컨텍스트 업데이트
            self._update_page_context(current_node, soup)
            
            # 전략 1: HTML 네비게이션 분석 (최우선)
            nav_path = current_node.extract_breadcrumb(soup, current_node.url)
            if nav_path != "unknown":
                self._validate_and_store_path(current_node.url, nav_path)
                logger.debug(f"🎯 네비게이션 기반 경로: {nav_path}")
                return nav_path
            
            # 전략 2: 전역 네비게이션 맵 활용
            global_path = self._find_path_in_global_map(current_node.url)
            if global_path:
                logger.debug(f"🗺️ 전역 맵 기반 경로: {global_path}")
                return global_path
            
            # 전략 3: 부모 경로 상속 + 현재 페이지 분석
            inherited_path = self._build_inherited_breadcrumb(current_node, soup)
            if inherited_path != "unknown":
                logger.debug(f"🔗 상속 기반 경로: {inherited_path}")
                return inherited_path
            
            # 전략 4: URL 패턴 분석 (최후 수단)
            pattern_path = self._infer_path_from_url(current_node.url)
            logger.debug(f"🔍 패턴 기반 경로: {pattern_path}")
            return pattern_path
            
        except Exception as e:
            logger.debug(f"컨텍스트 인식 경로 결정 실패: {e}")
            return "unknown"
    
    def _build_inherited_breadcrumb(self, current_node: URLTreeNode, soup: BeautifulSoup) -> str:
        """부모의 breadcrumb을 상속받고 자신의 제목을 추가하여 계층적 경로 구성"""
        try:
            # 부모 노드의 브레드크럼 경로 가져오기
            parent_path = ""
            if current_node.parent and current_node.parent.breadcrumb != "unknown":
                parent_path = current_node.parent.breadcrumb
            
            # 현재 페이지의 제목 추출 (여러 방법 시도)
            current_title = self._extract_current_page_title(current_node, soup)
            
            # 계층적 경로 구성
            if parent_path and current_title:
                inherited_path = f"{parent_path}/{current_title}"
                logger.debug(f"🔗 상속된 메뉴 경로: {inherited_path}")
                return inherited_path
            elif current_title:
                logger.debug(f"🆕 새로운 메뉴 경로: {current_title}")
                return current_title
            elif parent_path:
                # 제목을 찾지 못한 경우 URL에서 추출 시도
                url_title = self._extract_title_from_url(current_node.url)
                if url_title:
                    inherited_path = f"{parent_path}/{url_title}"
                    logger.debug(f"🔍 URL 기반 메뉴 경로: {inherited_path}")
                    return inherited_path
                else:
                    logger.debug(f"⚠️ 부모 경로만 사용: {parent_path}")
                    return parent_path
            else:
                # 마지막 수단: URL 패턴 기반 추정
                fallback_path = self._infer_path_from_url(current_node.url)
                logger.debug(f"🎯 대체 경로: {fallback_path}")
                return fallback_path
                
        except Exception as e:
            logger.debug(f"상속된 메뉴 경로 구성 실패: {e}")
            return "unknown"
    
    def _update_global_navigation_map(self, soup: BeautifulSoup, current_node: URLTreeNode) -> None:
        """전역 네비게이션 맵 업데이트"""
        try:
            # 네비게이션 구조 추출
            nav_structure = self._extract_navigation_structure(soup, current_node.url)
            
            # 전역 맵에 병합 (기존 정보 보존)
            for nav_path, nav_info in nav_structure.items():
                if nav_path not in self.global_navigation_map:
                    self.global_navigation_map[nav_path] = nav_info
                else:
                    # 기존 정보와 병합
                    self.global_navigation_map[nav_path].update(nav_info)
            
            logger.debug(f"🗺️ 전역 네비게이션 맵 업데이트: {len(nav_structure)}개 항목 추가")
            
        except Exception as e:
            logger.debug(f"전역 네비게이션 맵 업데이트 실패: {e}")
    
    def _update_page_context(self, current_node: URLTreeNode, soup: BeautifulSoup) -> None:
        """페이지별 컨텍스트 정보 업데이트"""
        try:
            page_context = {
                'url': current_node.url,
                'title': current_node.page_title,
                'page_type': current_node.page_type,
                'navigation_links': current_node.navigation_links,
                'parent_path': current_node.parent.breadcrumb if current_node.parent else None,
                'depth': current_node.depth
            }
            
            self.page_contexts[current_node.url] = page_context
            
        except Exception as e:
            logger.debug(f"페이지 컨텍스트 업데이트 실패: {e}")
    
    def _extract_navigation_structure(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Dict[str, Any]]:
        """현재 페이지에서 네비게이션 구조 추출"""
        nav_structure = {}
        
        try:
            # 기존 _analyze_ul_li_hierarchy 활용
            nav_containers = soup.select([
                'nav', '.nav', '.navigation', '.menu', '.gnb', '.lnb',
                '[class*="menu"]', '[id*="menu"]', '[class*="nav"]', '[id*="nav"]'
            ])
            
            for nav in nav_containers:
                extracted_links, extracted_menu_info = self._analyze_ul_li_hierarchy(nav, base_url, depth=0)
                
                # 메뉴 정보를 구조화
                for menu_item in extracted_menu_info:
                    if ':' in menu_item:
                        parts = menu_item.split(':', 3)
                        if len(parts) >= 3:
                            menu_type, menu_url, menu_path = parts[0], parts[1], parts[2]
                            
                            nav_structure[menu_url] = {
                                'path': menu_path,
                                'type': menu_type,
                                'source_url': base_url
                            }
            
        except Exception as e:
            logger.debug(f"네비게이션 구조 추출 실패: {e}")
        
        return nav_structure
    
    def _find_path_in_global_map(self, url: str) -> str:
        """전역 네비게이션 맵에서 URL에 해당하는 경로 찾기"""
        try:
            if url in self.global_navigation_map:
                return self.global_navigation_map[url].get('path', '')
            
            # URL 정규화하여 다시 시도
            normalized_url = self.normalize_url(url)
            if normalized_url in self.global_navigation_map:
                return self.global_navigation_map[normalized_url].get('path', '')
            
        except Exception as e:
            logger.debug(f"전역 맵에서 경로 찾기 실패: {e}")
        
        return ""
    
    def _validate_and_store_path(self, url: str, path: str) -> bool:
        """브레드크럼 경로 검증 및 저장"""
        try:
            # 기본 검증
            if not path or path == "unknown":
                return False
            
            # 경로 길이 검증 (너무 깊지 않은지)
            if len(path.split('/')) > 6:
                logger.debug(f"경로가 너무 깊음: {path}")
                return False
            
            # 중복 경로 검증 (같은 경로가 다른 URL에 사용되지 않았는지)
            if path in self.used_breadcrumbs:
                logger.debug(f"중복 경로 발견: {path}")
                # 중복이어도 허용 (같은 페이지가 여러 경로로 접근 가능)
            
            # 경로 저장
            self.used_breadcrumbs.add(path)
            return True
            
        except Exception as e:
            logger.debug(f"경로 검증 실패: {e}")
            return False
    
    def _extract_current_page_title(self, current_node: URLTreeNode, soup: BeautifulSoup) -> str:
        """현재 페이지의 제목을 여러 방법으로 추출"""
        try:
            # 게시글 보기 페이지의 경우 게시글 제목 추출
            if self._is_article_view_page(current_node.url):
                article_title = self._extract_article_title(soup, current_node.url)
                if article_title:
                    return article_title
            
            # artclList.do 페이지의 경우 "게시판" + 페이지 번호로 설정
            if 'artclList.do' in current_node.url:
                # URL에서 페이지 번호 추출
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(current_node.url)
                query_params = parse_qs(parsed.query)
                page_num = query_params.get('page', [None])[0]
                
                base_title = "게시판"
                
                # 페이지 번호가 있으면 추가
                if page_num and page_num != '1':  # 1페이지가 아닌 경우만 표시
                    return f"{base_title} {page_num}page"
                return base_title
            
            # 1. 이미 추출된 페이지 제목 사용
            if current_node.page_title and current_node.page_title != "제목없음":
                clean_title = current_node.page_title.strip()
                # 사이트명 제거
                if ' - ' in clean_title:
                    clean_title = clean_title.split(' - ')[0].strip()
                if clean_title and len(clean_title) <= 50:  # 너무 긴 제목 방지
                    return clean_title
            
            # 2. h1, h2 태그에서 추출
            if soup:
                for tag in ['h1', 'h2', '.page-title', '.title', '.subject']:
                    element = soup.select_one(tag)
                    if element:
                        text = element.get_text().strip()
                        if text and len(text) <= 50:
                            return text
            
            # 3. URL에서 추출
            url_title = self._extract_title_from_url(current_node.url)
            if url_title:
                return url_title
            
            return ""
            
        except Exception as e:
            logger.debug(f"현재 페이지 제목 추출 실패: {e}")
            return ""
    

    
    def _extract_article_title(self, soup: BeautifulSoup, url: str) -> str:
        """범용적인 게시글 제목 추출"""
        try:
            # 게시글 보기 페이지가 아닌 경우 빈 문자열 반환
            if not self._is_article_view_page(url):
                return ""
            
            # 패턴 1: view-title, post-title 등 게시글 제목 전용 클래스
            title_selectors = [
                'h1.view-title', 'h2.view-title', 'h3.view-title',
                'h1.post-title', 'h2.post-title', 'h3.post-title', 
                'h1.article-title', 'h2.article-title', 'h3.article-title',
                '.view-title h1', '.view-title h2', '.post-title h1', '.post-title h2',
                '.article-title h1', '.article-title h2', '.entry-title',
                'h1.title', 'h2.title', 'h3.title',
                '.title h1', '.title h2', '.title h3'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text().strip():
                    title = title_elem.get_text().strip()
                    if self._is_valid_article_title(title):
                        return title
            
            # 패턴 2: 첫 번째 h1, h2 태그 (사이트 제목이 아닌 경우)
            for tag in ['h1', 'h2']:
                heading = soup.find(tag)
                if heading and heading.get_text().strip():
                    title = heading.get_text().strip()
                    if self._is_valid_article_title(title):
                        return title
            
            # 패턴 3: title 태그에서 추출 (사이트명 제거)
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
                # 사이트명 제거 시도
                if ' - ' in title:
                    title_parts = title.split(' - ')
                    for part in title_parts:
                        part = part.strip()
                        if self._is_valid_article_title(part):
                            return part
                elif self._is_valid_article_title(title):
                    return title
            
            return ""
            
        except Exception as e:
            logger.debug(f"게시글 제목 추출 실패: {e}")
            return ""
    
    def _is_article_view_page(self, url: str) -> bool:
        """게시글 보기 페이지인지 판단"""
        try:
            # 일반적인 게시글 보기 페이지 패턴들
            article_patterns = [
                'artclView.do', 'articleView.do', 'boardView.do',
                'view.do', 'detail.do', 'read.do',
                '/view/', '/detail/', '/read/', '/article/',
                '/post/', '/board/view', '/bbs/view'
            ]
            
            url_lower = url.lower()
            return any(pattern.lower() in url_lower for pattern in article_patterns)
            
        except Exception as e:
            logger.debug(f"게시글 보기 페이지 판단 실패: {e}")
            return False
    
    def _is_valid_article_title(self, title: str) -> bool:
        """유효한 게시글 제목인지 판단 (사이트명이나 일반적인 제목 제외)"""
        try:
            if not title or not title.strip():
                return False
            
            title = title.strip()
            
            # 너무 짧거나 긴 제목 제외
            if len(title) < 2 or len(title) > 200:
                return False
            
            # 일반적인 사이트 제목이나 기본 페이지 제목 제외
            invalid_titles = [
                '제목없음', '페이지', '홈', '메인', '로딩', 'loading',
                '에러', 'error', '404', '500', '접근권한',
                '로그인', 'login', '회원가입', 'join'
            ]
            
            title_lower = title.lower()
            for invalid in invalid_titles:
                if invalid.lower() in title_lower:
                    return False
            
            # 사이트명으로 보이는 패턴 제외 (대학교, 회사명 등)
            site_patterns = ['대학교', '대학', 'university', '회사', 'company', '기관', '재단']
            if any(pattern in title for pattern in site_patterns) and len(title) < 15:
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"게시글 제목 유효성 검사 실패: {e}")
            return False
    

    
    def _get_page_type_title(self, current_node: URLTreeNode) -> str:
        """페이지 타입에 따른 기본 제목 반환"""
        if current_node.is_document:
            return "문서"
        elif current_node.page_type == "board":
            return "게시판"
        elif current_node.page_type == "main":
            return "메인"
        else:
            return "페이지"
    
    def _extract_title_from_url(self, url: str) -> str:
        """URL에서 의미있는 제목 추출"""
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            
            # 쿼리 파라미터에서 정보 추출
            query_params = parse_qs(parsed.query)
            
            # artclView.do 같은 게시글 보기 페이지인 경우
            if 'artclView.do' in url:
                if 'artclNo' in query_params:
                    return f"게시글_{query_params['artclNo'][0]}"
                return "게시글"
            
            # artclList.do 같은 게시판 목록 페이지인 경우
            if 'artclList.do' in url:
                return "게시판"
            
            # 다운로드 파일인 경우
            if any(pattern in url.lower() for pattern in ['download', 'file']):
                return "첨부파일"
            
            # URL 경로에서 의미있는 부분 추출
            path_parts = [p for p in parsed.path.split('/') if p and p not in ['index.do', 'main.do']]
            if path_parts:
                last_part = path_parts[-1]
                # 파일 확장자 제거
                clean_part = re.sub(r'\.(do|html|htm|jsp|php)$', '', last_part)
                
                # 의미있는 이름으로 변환
                segment_mappings = {
                    'artcllist': '목록',
                    'artclview': '상세보기',
                    'professor': '교수진',
                    'faculty': '교수진',
                    'curriculum': '교육과정',
                    'research': '연구',
                    'notice': '공지사항',
                    'news': '소식',
                    'intro': '소개',
                    'about': '소개',
                    'subview': '페이지'
                }
                
                return segment_mappings.get(clean_part.lower(), clean_part)
            
            return ""
            
        except Exception as e:
            logger.debug(f"URL 제목 추출 실패: {e}")
            return ""

def main(start_url, scope=None, max_pages=10000, delay=1.0, timeout=20, use_requests=True, verbose=False, max_depth=10, generate_extra_files=None, max_pagination_pages=30):
    """매개변수로 크롤러 실행 (DFS 방식)"""
    if verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
    
    # 시작 시간 기록
    start_time = time.time()
    
    # URL 정규화 및 공백 제거
    start_url = start_url.strip()
    if not start_url.startswith(('http://', 'https://')):
        start_url = 'https://' + start_url
    
    logger.info(f"🚀 크롤링 시작: {start_url}")
    
    if generate_extra_files:
        logger.debug(f"📊 추가 파일 생성 예정: {generate_extra_files}")
    
    with ScopeLimitedCrawler(max_pages=max_pages, delay=delay, timeout=timeout, 
                            use_requests=use_requests, max_depth=max_depth, max_pagination_pages=max_pagination_pages) as crawler:
        
        # DFS 크롤링 실행
        results = crawler.discover_urls_dfs(start_url, scope)
            
        # 추가 파일 생성 (옵션)
        if generate_extra_files and results and "results_dir" in results:
            logger.debug(f"📊 추가 파일 생성 중...")
            extra_files = crawler.generate_derived_files(results["results_dir"], generate_extra_files)
            results["extra_files"] = extra_files
            logger.debug(f"✅ 추가 파일 생성 완료: {len(extra_files)}개")
            
        # 실행 시간 계산
        execution_time = time.time() - start_time
        
        if results:
            results["execution_time_seconds"] = execution_time
            base_files = 6 if results.get("visualization_file") else 5  # 기본 5개 + 그래프 1개
            extra_files_count = len(results.get("extra_files", {})) if generate_extra_files else 0
            total_files = base_files + extra_files_count
            
            logger.info(f"🎉 크롤링 완료! 실행 시간: {execution_time:.2f}초, 파일: {total_files}개")
        
        return results

def extract_document_urls_from_results(results: Dict[str, Any]) -> List[str]:
    """
    크롤링 결과에서 문서 URL 목록을 추출
    
    Args:
        results: discover_urls 메서드의 반환값
        
    Returns:
        문서 URL 목록
    """
    if not results or "doc_urls" not in results:
        return []
    
    doc_urls = results["doc_urls"]
    if isinstance(doc_urls, set):
        return list(doc_urls)
    elif isinstance(doc_urls, list):
        return doc_urls
    else:
        return []

if __name__ == "__main__":
    # 테스트 실행 예시
    results = main(
        # start_url="https://spri.kr/",
        # start_url="https://cse.snu.ac.kr/",
        start_url="https://www.oss.kr/",
        scope=None,
        max_pages=99999,
        delay=0.5,
        timeout=10,
        use_requests=True,
        verbose=True,
        max_depth=10
    )
    
    if results and "error" not in results:
        print(f"✅ DFS 크롤링 완료 (4개 카테고리 분류):")
        print(f"   📊 페이지: {len(results.get('page_urls', []))}개")
        print(f"   📄 문서: {len(results.get('doc_urls', []))}개")
        print(f"   🏷️ 분류: Main(1), document, board, general")
        if results.get('doc_urls_file'):
            print(f"   📋 문서 URL 파일: {os.path.basename(results['doc_urls_file'])}")
    else:
        print(f"❌ 크롤링 실패: {results.get('error', '알 수 없는 오류')}")