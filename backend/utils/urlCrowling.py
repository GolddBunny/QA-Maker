from bs4 import BeautifulSoup
import os
import time
import random
import re
import json
import logging
from urllib.parse import urlparse, urljoin, parse_qs
from datetime import datetime
from typing import Set, List, Dict, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSelectorException

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
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "@input")
# 유저 에이전트 정의
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]
# 문서 파일 확장자 패턴
DOC_EXTENSIONS = ['.pdf', '.docx', '.doc', '.hwp', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.jpg', '.jpeg', '.png', '.svg', '.webp']
# 제외할 url 패턴
EXCLUDE_PATTERNS = [
    '/login', '/logout', '/search?', 'javascript:', '#', 'mailto:', 'tel:',
    '/api/', '/rss/', 'comment', 'download.do', 'print.do', 'popup', 'redirect', 'captcha', 'admin', 'synapView.do?', '/synapView.do?', '/synap', '/synap/view.do', '/synap/view.do?'
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
    'filearea', 'file-area', 'download-area', 'download-box'
]
# 다운로드 URL 패턴
DOWNLOAD_PATTERNS = [
    '/download', '/file', '/attach', 'fileDown', 'getFile', 
    'downloadFile', 'downFile', 'fileview'
]

class ScopeLimitedCrawler:
    def __init__(self, max_pages: int = 1000, delay: float = 1, timeout: int = 5, use_requests: bool = True):
        """크롤러 초기화.
        
        Args:
            max_pages: 크롤링할 최대 페이지 수
            delay: 요청 간 지연 시간(초)
            timeout: 페이지 로딩 시간 제한(초)
            use_requests: 간단한 페이지는 requests 사용, JS가 많은 페이지는 selenium 사용
        """
        self.visited_urls: Set[str] = set()  # 방문한 URL 집합
        self.excluded_urls: Set[str] = set()  # 제외된 URL 집합 (추가)
        self.base_domain: str = ""  # 기본 도메인
        self.scope_patterns: List[str] = []  # 크롤링 범위 패턴
        self.max_pages: int = max_pages  # 최대 페이지 수
        self.delay: float = delay  # 요청 간 지연 시간
        self.timeout: int = timeout  # 페이지 로딩 시간 제한
        self.use_requests: bool = use_requests  # requests 라이브러리 사용 여부
        self.session = requests.Session()  # 세션 생성
        self.session.headers.update({"User-Agent": random.choice(USER_AGENTS)})  # 랜덤 User-Agent 설정

        # 결과 저장 디렉토리
        os.makedirs(BASE_DIR, exist_ok=True)
        
        # Selenium 초기화 (필요할 때만)
        self.driver = None

    def _init_selenium(self) -> None:
        """Selenium WebDriver를 초기화"""
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
        
        # 성능 최적화 설정
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
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
        except Exception as e:
            logger.error(f"Selenium 드라이버 초기화 실패: {e}")
            # 실패 시 재시도
            try:
                time.sleep(1)
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(self.timeout)
            except Exception as e:
                logger.error(f"Selenium 드라이버 재초기화 실패: {e}")
                raise

    def __del__(self) -> None:
        """객체가 소멸될 때 Selenium 드라이버 종료"""
        self.close_driver()

    def close_driver(self) -> None:
        """Selenium 드라이버 안전하게 종료"""
        if hasattr(self, 'driver') and self.driver is not None:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("웹드라이버가 성공적으로 종료되었습니다")
            except Exception as e:
                logger.error(f"웹드라이버 종료 중 오류 발생: {e}")

    def normalize_url(self, url: str) -> str:
        """URL 정규화하여 프래그먼트와 후행 슬래시 제거"""
        # 프래그먼트 제거
        if '#' in url:
            url = url.split('#')[0]
        
        # 프로토콜 확인
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'https://' + url
        
        # 도메인 루트가 아닌 경우, 후행 슬래시 제거
        parsed = urlparse(url)
        if parsed.path == '/':
            return url
        return url.rstrip('/')

    def is_in_scope(self, url: str) -> bool:
        """URL이 정의된 크롤링 범위 내에 있는지 확인"""
        try:
            parsed = urlparse(url)
            
            # 도메인 확인 - 기본 도메인에 속해야 함
            if self.base_domain not in parsed.netloc:
                return False
                
            # 범위 패턴 일치 여부 확인
            url_path = parsed.path.lower()
            for pattern in self.scope_patterns:
                if pattern in url_path:
                    return True
            
            return False
        except Exception as e:
            logger.error(f"URL 범위 확인 중 오류 발생: {e}")
            return False
    
    def should_exclude_url(self, url: str) -> bool:
        """URL이 정의된 패턴에 따라 제외되어야 하는지 확인"""
        # 이미 제외로 확인된 URL인지 검사
        if url in self.excluded_urls:
            return True
            
        lower_url = url.lower()
        
        # 제외 패턴 확인
        for pattern in EXCLUDE_PATTERNS:
            if pattern in lower_url:
                logger.debug(f"제외 패턴 확인: {url}")
                self.excluded_urls.add(url)  # 제외 URL 목록에 추가
                return True
                
        return False

    def is_valid_file_url(self, href: str, base_url: str) -> bool:
        """URL이 유효한 파일 URL인지 확인"""
        if not href or href == '#' or href.startswith(('javascript:', 'mailto:', 'tel:')):
            return False
        
        lower_url = href.lower()
        
        # 파일 확장자 확인
        if any(lower_url.endswith(ext) for ext in DOC_EXTENSIONS):
            return True
            
        # 다운로드 URL 패턴 확인
        if any(pattern in lower_url for pattern in DOWNLOAD_PATTERNS):
            return True
            
        return False

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> Tuple[Set[str], Set[str]]:
        """페이지에서 일반 링크와 문서 링크 추출"""
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
                    # logger.debug(f"절대 URL 생성: {full_url}")
                else:
                    full_url = urljoin(base_url, href)
                
                full_url = self.normalize_url(full_url)
                
                # 이미 제외된 URL인지 빠르게 확인 (추가)
                if full_url in self.excluded_urls:
                    continue
                
                # 문서 파일인지 확인
                is_doc = False
                lower_url = full_url.lower()

                if 'download.do' in lower_url or any(pattern in lower_url for pattern in DOWNLOAD_PATTERNS):
                    doc_links.add(full_url)
                    is_doc = True
                else:
                    # 확장자 확인
                    for ext in DOC_EXTENSIONS:
                        if lower_url.endswith(ext):
                            doc_links.add(full_url)
                            is_doc = True
                            break
                
                # 일반 URL 추가 (제외 패턴 및 범위 확인)
                if not is_doc and not self.should_exclude_url(full_url) and self.is_in_scope(full_url):
                    links.add(full_url)

            # 2. 첨부파일 추출
            attachment_links = self.extract_attachments(soup, base_url)
            doc_links.update(attachment_links)
                    
            return links, doc_links
            
        except Exception as e:
            logger.error(f"링크 추출 중 오류 발생: {e}")
            return set(), set()

    def extract_attachments(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """페이지에서 첨부파일 링크 추출"""
        doc_links = set()
        
        try:
            # 1. 첨부파일 클래스 확인
            for class_name in ATTACHMENT_CLASSES:
                sections = soup.find_all(class_=lambda c: c and class_name in c.lower())
                for section in sections:
                    links = section.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        # synapview.do 링크 제외
                        if 'synapView.do' in href.lower():
                            continue

                        if self.is_valid_file_url(href, base_url):
                            if href.startswith('/'):
                                doc_links.add(f"https://{self.base_domain}{href}")
                            else:
                                doc_links.add(urljoin(base_url, href))
            
            # 2. 파일 관련 속성 확인
            file_related_elements = soup.find_all(
                ['a', 'span', 'div', 'li'], 
                attrs=lambda attr: attr and any(x in str(attr).lower() for x in ['file', 'attach', 'download'])
            )
            
            for element in file_related_elements:
                links = [element] if element.name == 'a' and element.has_attr('href') else element.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if self.is_valid_file_url(href, base_url):
                        if href.startswith('/'):
                            doc_links.add(f"https://{self.base_domain}{href}")
                        else:
                            doc_links.add(urljoin(base_url, href))
            
            # 3. 파일 확장자 직접 검색
            for link in soup.find_all('a', href=True):
                href = link['href']
                if self.is_valid_file_url(href, base_url):
                    if href.startswith('/'):
                        doc_links.add(f"https://{self.base_domain}{href}")
                    else:
                        doc_links.add(urljoin(base_url, href))
                    
            return doc_links
            
        except Exception as e:
            logger.error(f"첨부파일 추출 중 오류 발생: {e}")
            return set()

    def fetch_page(self, url: str) -> Tuple[bool, Any, str]:
        """설정에 따라 requests 또는 selenium을 사용하여 페이지 내용을 가져옴."""
        url = self.normalize_url(url)
        
        # JavaScript:로 시작하는 URL 처리
        if url.startswith('javascript:'):
            logger.debug(f"JavaScript URL 감지: {url}")
            return False, None, url
        
        # 먼저 requests 사용 시도 (활성화된 경우)
        if self.use_requests:
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                # 자바스크립트가 많은 페이지인지 확인
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 페이지가 자바스크립트를 필요로 하는 것 같으면 Selenium으로 전환
                noscript_content = soup.find('noscript')
                js_required = noscript_content and len(noscript_content.text) > 100
                
                if not js_required:
                    return True, soup, response.url
                    
            except Exception as e:
                logger.debug(f"Requests 가져오기 실패, Selenium으로 전환: {e}")
                # Selenium으로 대체 
        
        # requests가 실패하거나 자바스크립트가 필요한 경우 Selenium 사용    
        try:
            self._init_selenium()
            
            # 최대 2번 재시도 
            for attempt in range(2):
                try:
                    self.driver.get(url)
                    
                    # 페이지 로드 대기
                    WebDriverWait(self.driver, self.timeout).until(
                        EC.presence_of_element_located((By.TAG_NAME, 'body'))
                    )
                    
                    html_content = self.driver.page_source
                    current_url = self.driver.current_url
                    
                    soup = BeautifulSoup(html_content, 'html.parser')
                    return True, soup, current_url
                except TimeoutException:
                    if attempt < 1:  # 첫 번째 시도가 실패한 경우에만 재시도
                        logger.warning(f"페이지 로딩 타임아웃, 재시도 중: {url}")
                        continue
                    raise
                
        except Exception as e:
            logger.error(f"Selenium으로 페이지 가져오기 중 오류 발생: {e}")
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
        
        # 1. 페이지네이션 요소 감지
        has_pagination, pagination_element = self.detect_pagination(soup)
        
        # 페이지네이션 요소가 감지되었을 때 로그 출력
        if has_pagination:
            logger.debug(f"페이지네이션 요소 감지: {has_pagination}, URL: {current_url}")
        
        if not has_pagination:
            return pagination_urls
        
        # 2. 페이지 URL 패턴과 마지막 페이지 번호 파악
        url_pattern, last_page = self._extract_pagination_pattern(soup, current_url, pagination_element)
        
        logger.debug(f"URL 패턴: {url_pattern}, 마지막 페이지: {last_page}")
        
        # 3. 다음 페이지 버튼 처리 (JavaScript 포함)
        js_links = []
        direct_links = []
        
        # 페이지네이션 버튼 찾기
        if pagination_element:
            for a in pagination_element.find_all('a', href=True):
                href = a['href']
                if href and href != '#':
                    if href.startswith('javascript:'):
                        js_links.append(href)
                    else:
                        # 일반 링크
                        full_url = urljoin(current_url, href)
                        if self.is_in_scope(full_url):
                            direct_links.append(self.normalize_url(full_url))
        
        # 페이지네이션 정보 로깅
        total_pages = len(direct_links) + len(js_links)
        if total_pages > 0:
            logger.info(f"[{len(self.visited_urls)}/{self.max_pages}] 페이지네이션 발견: {total_pages}개 페이지")
        
        # 직접 페이지 링크 추가
        pagination_urls.extend(direct_links)
        
        # JavaScript 페이지 처리 (최대 100페이지로 제한하여 성능 최적화)
        js_pages_to_process = min(100, len(js_links))
        for i in range(js_pages_to_process):
            js_link = js_links[i]
            logger.info(f"다음 페이지 버튼 발견: {js_link}")
            
            # JavaScript 페이지 처리
            page_soup, page_url = self.handle_javascript_pagination(current_url, js_link)
            if page_soup and page_url:
                # 페이지네이션 URL 저장
                normalized_url = self.normalize_url(page_url)
                if normalized_url not in pagination_urls and normalized_url != current_url:
                    pagination_urls.append(normalized_url)
                    logger.info(f"JavaScript 페이지네이션 URL 추가: {normalized_url}")

                # 페이지에서 링크 추출
                links, docs = self.extract_links(page_soup, page_url)
                
                # 문서 URL 저장
                for doc_url in docs:
                    if doc_url not in self.visited_urls:
                        self.all_doc_urls.add(doc_url)
                        logger.info(f"[{len(self.visited_urls)}/{self.max_pages}] Document found: {doc_url}")
                
        # 4. URL 패턴이 있고 마지막 페이지 번호가 있는 경우, 모든 페이지 URL 생성
        if url_pattern and last_page > 0:
            for page_num in range(1, last_page + 1):
                page_url = url_pattern.replace('{page}', str(page_num))
                normalized_url = self.normalize_url(page_url)
                if normalized_url not in pagination_urls and normalized_url != current_url:
                    pagination_urls.append(normalized_url)
                    logger.info(f"패턴 기반 페이지네이션 URL 추가: {normalized_url}")
        
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
                                pagination_urls.add(self.normalize_url(full_url))
                                
                # 다음 버튼 확인
                next_buttons = soup.select('a.next, a.nextpage, a[rel="next"]')
                for btn in next_buttons:
                    if btn.has_attr('href'):
                        href = btn['href']
                        if href and href != '#' and not href.startswith('javascript:'):
                            full_url = urljoin(current_url, href)
                            if self.is_in_scope(full_url):
                                pagination_urls.add(self.normalize_url(full_url))
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
                                pagination_urls.add(self.normalize_url(href))
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
                                    pagination_urls.add(self.normalize_url(href))
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
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc
        
        # 사이트맵 URL 추적을 위한 집합 초기화
        processed_sitemaps = set()
        
        # 범위 패턴 설정
        if scope_patterns:
            self.scope_patterns = [p.lower() for p in scope_patterns]
        else:
            # 시작 URL 경로에서 범위 패턴 추출
            path_parts = parsed_url.path.lower().split('/')
            for part in path_parts:
                if part and part not in ['sites', 'index.do', 'web']:
                    self.scope_patterns.append(part.lower())
        
        # 범위 패턴이 추출되지 않은 경우
        if not self.scope_patterns:
            logger.warning("범위 패턴이 지정되지 않았습니다. 도메인 전체 범위 사용.")
        
        # 컬렉션 초기화
        all_page_urls = set()
        self.all_doc_urls = set()  # 모든 문서 URL 추적
        queue = [start_url]
        visited = set()
        current_page = 0
        
        # 파일 이름 생성을 위한 타임스탬프와 범위 이름 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        scope_name = '_'.join(self.scope_patterns) if self.scope_patterns else 'full_domain'
        
        # 도메인 디렉토리 생성
        domain_name = self.base_domain.replace('.', '_')
        domain_base_dir = os.path.join(BASE_DIR, f"{domain_name}_{scope_name}")
        domain_dir = os.path.join(domain_base_dir, timestamp)
        os.makedirs(domain_dir, exist_ok=True)
        
        logger.info(f"URL 발견 시작: {start_url}")
        logger.info(f"기본 도메인: {self.base_domain}")
        logger.info(f"범위 패턴: {self.scope_patterns}")
        logger.info(f"최대 페이지: {self.max_pages}")
        
        try:
            # 시작 URL 수집
            with ThreadPoolExecutor(max_workers=1) as executor:
                # 제어된 크롤링을 위한 단일 작업자 사용
                while queue and current_page < self.max_pages:
                    try:
                        current_url = queue.pop(0)

                        # 중복 방문 및 순환 감지
                        if current_url in visited:
                            continue
                        
                        # URL 형식 확인
                        if not (current_url.startswith('http://') or current_url.startswith('https://')):
                            continue
                            
                        # URL이 범위 내에 있는지 확인
                        if not self.is_in_scope(current_url):
                            continue
                        
                        # URL 처리 디버깅 로그 추가
                        logger.debug(f"URL 체크: {current_url}, 범위 내: {self.is_in_scope(current_url)}")
                        
                        # 루프 감지 - 큐의 처음 몇 개 항목과 현재 URL 비교
                        loop_detected = False
                        check_count = min(5, len(queue))
                        for i in range(check_count):
                            if queue[i] == current_url:
                                logger.warning(f"URL 루프 감지: {current_url}, 건너뜀")
                                loop_detected = True
                                break
                        
                        if loop_detected:
                            continue
                        
                        # 사이트맵 URL인지 확인하고 아직 처리하지 않았는지 확인
                        if self.is_sitemap_url(current_url) and current_url not in processed_sitemaps:
                            progress = f"[{current_page}/{self.max_pages}]"
                            logger.info(f"{progress} 사이트맵 발견: {current_url}")
                            processed_sitemaps.add(current_url)
                            
                            # 사이트맵에서 모든 링크 추출
                            sitemap_links = self.handle_sitemap(current_url)
                            logger.info(f"사이트맵에서 추출한 링크 수: {len(sitemap_links)}")
                            
                            # 우선순위: 새 링크를 큐의 앞에 추가
                            new_links = [link for link in sitemap_links 
                                        if link not in visited and link not in queue and link != current_url]
                            
                            if new_links:
                                logger.info(f"{progress} {len(new_links)}개 사이트맵 링크를 큐에 추가")
                                # 우선 처리를 위해 큐의 시작 부분에 삽입
                                queue = new_links + queue 
                            
                            # 사이트맵을 방문한 것으로 표시
                            visited.add(current_url)
                            all_page_urls.add(current_url)
                            
                            # 다음 URL로 계속
                            time.sleep(self.delay)
                            continue
                            
                        # 진행 상황 추적        
                        current_page += 1
                        progress = f"[{current_page}/{self.max_pages}]"
                        logger.info(f"{progress} 발견: {current_url}")
                        
                        # 페이지 가져오기
                        success, content, current_url = self.fetch_page(current_url)
                        
                        if not success:
                            visited.add(current_url)  # 재시도 방지용 방문 표시 
                            continue
                        
                        # 방문으로 표시하고 결과에 추가 
                        visited.add(current_url)
                        all_page_urls.add(current_url)
                        
                        # BeautifulSoup 사용 시 링크 가져오기
                        if isinstance(content, BeautifulSoup):
                            soup = content
                            links, documents = self.extract_links(soup, current_url)
                            
                            # 문서 URL 저장
                            for doc_url in documents:
                                if doc_url not in self.all_doc_urls:
                                    self.all_doc_urls.add(doc_url)
                                    logger.info(f"{progress} Document found: {doc_url}")
                            
                            # 페이지네이션 처리
                            pagination_urls = self.handle_pagination(soup, current_url)
                            
                            # 일반 링크를 큐에 추가
                            for link in links:
                                if link not in visited and link not in queue:
                                    queue.append(link)
                            
                            # 페이지네이션 URL도 큐에 추가
                            for page_url in pagination_urls:
                                if page_url not in visited and page_url not in queue:
                                    queue.append(page_url)
                        
                        else:
                            # Selenium 결과 사용
                            self._init_selenium()
                            html_content = self.driver.page_source
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            links, documents = self.extract_links(soup, current_url)
                            
                            # 문서 URL 저장
                            for doc_url in documents:
                                if doc_url not in self.all_doc_urls:
                                    self.all_doc_urls.add(doc_url)
                                    logger.info(f"{progress} Document found: {doc_url}")
                            
                            # 페이지네이션 처리
                            pagination_urls = self.handle_pagination(soup, current_url)
                            
                            # 일반 링크를 큐에 추가
                            for link in links:
                                if link not in visited and link not in queue:
                                    queue.append(link)
                            
                            # 페이지네이션 URL도 큐에 추가
                            for page_url in pagination_urls:
                                if page_url not in visited and page_url not in queue:
                                    queue.append(page_url)
                        
                        # 요청 간 지연 추가
                        time.sleep(self.delay)
                        
                    except Exception as e:
                        logger.error(f"{progress} Error processing URL: {current_url}, Error: {e}")
            
            # 실행 시간 계산
            execution_time = time.time() - start_time
            
            # 결과 저장
            results_data = self._save_results(
                all_page_urls, 
                self.all_doc_urls, 
                domain_dir, 
                timestamp, 
                start_url,
                scope_name,
                execution_time
            )
            
            logger.info(f"\nURL 발견 완료:")
            logger.info(f"발견된 페이지: {len(all_page_urls)}개, 문서: {len(self.all_doc_urls)}개")
            logger.info(f"결과 저장: {domain_dir}")
            logger.info(f"실행 시간: {execution_time:.1f}초")
            
            return results_data
        
        except Exception as e:
            logger.error(f"URL 발견 실패: {e}")
            return {
                "page_urls": all_page_urls,
                "doc_urls": self.all_doc_urls,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        
        finally:
            # 드라이버 종료 
            self.close_driver()

    def _save_results(self, page_urls, doc_urls, domain_dir, timestamp, start_url, scope_name, execution_time):
        """크롤러 결과를 파일에 저장"""
        # URL 목록 저장
        page_urls_file = os.path.join(domain_dir, f"page_urls_{timestamp}.txt")
        doc_urls_file = os.path.join(domain_dir, f"document_urls_{timestamp}.txt")
        
        self._save_urls_to_file(page_urls, page_urls_file)
        self._save_urls_to_file(doc_urls, doc_urls_file)
        
        # 메타데이터와 함께 JSON 결과 저장
        patterns_analysis = self.analyze_url_patterns(page_urls)
        
        json_data = {
            "timestamp": timestamp,
            "execution_time_seconds": execution_time,
            "base_url": start_url,
            "base_domain": self.base_domain,
            "scope_patterns": self.scope_patterns,
            "scope_name": scope_name,
            "total_pages_discovered": len(page_urls),
            "total_documents_discovered": len(doc_urls),
            "page_urls": list(page_urls),
            "document_urls": list(doc_urls),
            "url_patterns": patterns_analysis
        }
        
        json_file = os.path.join(domain_dir, f"crawl_results_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        return {
            "page_urls": page_urls,
            "doc_urls": doc_urls,
            "results_dir": domain_dir,
            "json_file": json_file,
            "execution_time": execution_time,
            "patterns_analysis": patterns_analysis
        }

    def _save_urls_to_file(self, urls: Set[str], filepath: str) -> None:
        """URL 목록을 파일에 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for url in sorted(urls):
                f.write(f"{url}\n")
        logger.info(f"URL 목록 저장: {filepath}")
    
    def analyze_url_patterns(self, urls: Set[str]) -> Dict[str, Any]:
        """발견된 URL의 패턴 분석"""
        patterns = {}
        domains = {}
        path_segments = {}
        query_params = {}
        
        for url in urls:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # 도메인 카운트
            domains[domain] = domains.get(domain, 0) + 1
            
            # 경로 패턴 추출
            path = parsed.path
            path_parts = path.strip('/').split('/')
            
            # 숫자를 패턴으로 변환
            pattern_parts = []
            for part in path_parts:
                if not part:
                    continue
                if part.isdigit():
                    pattern_parts.append('{id}')
                elif re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', part):
                    pattern_parts.append('{uuid}')
                elif re.match(r'^(19|20)\d\d[01]\d[0-3]\d$', part):
                    pattern_parts.append('{date}')
                else:
                    pattern_parts.append(part)
            
            if pattern_parts:
                pattern = '/' + '/'.join(pattern_parts)
                patterns[pattern] = patterns.get(pattern, 0) + 1
            
            # 경로 세그먼트 분석
            for i, part in enumerate(path_parts):
                if not part:
                    continue
                
                segment_key = f"segment_{i+1}"
                if segment_key not in path_segments:
                    path_segments[segment_key] = {}
                
                path_segments[segment_key][part] = path_segments[segment_key].get(part, 0) + 1
            
            # 쿼리 매개변수 분석
            if parsed.query:
                query_parts = parsed.query.split('&')
                for part in query_parts:
                    if '=' in part:
                        param_name = part.split('=')[0]
                        query_params[param_name] = query_params.get(param_name, 0) + 1
        
        # 결과 정렬
        sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        
        # 경로 세그먼트 데이터 정렬
        sorted_segments = {}
        for segment, values in path_segments.items():
            sorted_segments[segment] = sorted(values.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 쿼리 매개변수 정렬
        sorted_params = sorted(query_params.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "domains": sorted_domains,
            "patterns": sorted_patterns[:30],
            "segments": sorted_segments,
            "query_params": sorted_params[:20]
        }
    
    def is_sitemap_url(self, url: str) -> bool:
        """URL이 사이트맵 페이지인지 확인"""
        lower_url = url.lower()
        return ('sitemap' in lower_url or 'site-map' in lower_url or 'site_map' in lower_url)
    
    def handle_sitemap(self, url: str) -> Set[str]:
        """사이트맵 페이지에서 모든 링크를 추출하여 집합으로 반환"""
        sitemap_links = set()
        
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
                                normalized_url = self.normalize_url(full_url)
                                sitemap_links.add(normalized_url)
            
            logger.info(f"사이트맵에서 {len(sitemap_links)}개 링크 추출: {url}")
            
            # XML 사이트맵 링크도 확인
            xml_sitemap_links = soup.select('a[href*="sitemap.xml"]')
            if xml_sitemap_links:
                for link in xml_sitemap_links:
                    href = link.get('href')
                    if href:
                        xml_url = urljoin(url, href)
                        xml_links = self.parse_xml_sitemap(xml_url)
                        sitemap_links.update(xml_links)
                        
            return sitemap_links
            
        except Exception as e:
            logger.error(f"사이트맵 처리 중 오류 발생 {url}: {e}")
            return sitemap_links

    def parse_xml_sitemap(self, url: str) -> Set[str]:
        """XML 사이트맵을 파싱하고 모든 URL 추출"""
        xml_links = set()
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                url_tags = soup.find_all('loc')
                
                for tag in url_tags:
                    link = tag.text.strip()
                    if self.is_in_scope(link) and not self.should_exclude_url(link):
                        xml_links.add(self.normalize_url(link))
                        
                logger.info(f"XML 사이트맵에서 {len(xml_links)}개 링크 추출: {url}")
            
            return xml_links
            
        except Exception as e:
            logger.error(f"XML 사이트맵 파싱 중 오류 발생 {url}: {e}")
            return xml_links


def parse_arguments():
    """명령줄 인수 구문 분석"""
    import argparse
    
    parser = argparse.ArgumentParser(description="범위 제한 웹 크롤러")
    
    parser.add_argument('--start-url', '-u', type=str, required=True, help='크롤링 시작 URL')
    
    parser.add_argument('--scope', '-s', type=str, nargs='+', help='크롤링 범위 제한 (예: "cse" "department")')
    
    parser.add_argument('--max-pages', '-m', type=int, default=1000, help='크롤링할 최대 페이지 수 (기본: 1000)')
    
    parser.add_argument('--delay', '-d', type=float, default=1.0, help='요청 간 지연 시간 (기본: 1초)')
    
    parser.add_argument('--timeout', '-t', type=int, default=20, help='페이지 로드 타임아웃 (기본: 20초)')
    
    parser.add_argument('--use-requests', '-r', action='store_true', help='가능한 경우 더 빠른 크롤링을 위해 requests 라이브러리 사용')
    
    parser.add_argument('--verbose', '-v', action='store_true', help='자세한 로깅 활성화')
    
    return parser.parse_args()


def main():
    """명령줄에서 크롤러 실행"""
    args = parse_arguments()
    
    # 로깅 레벨 구성
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    logger.info(f"URL 크롤러 시작: {args.start_url}")
    logger.info(f"범위 패턴: {args.scope}")
    
    # 크롤러 생성 및 실행
    crawler = ScopeLimitedCrawler(
        max_pages=args.max_pages, 
        delay=args.delay, 
        timeout=args.timeout,
        use_requests=args.use_requests
    )
    
    try:
        results = crawler.discover_urls(args.start_url, args.scope)
        
        if results:
            logger.info("\n크롤링 요약:")
            logger.info(f"발견된 페이지: {len(results['page_urls'])}개")
            logger.info(f"발견된 문서: {len(results['doc_urls'])}개")
            logger.info(f"결과 저장 위치: {results['results_dir']}")
            logger.info(f"실행 시간: {results.get('execution_time', 0):.1f}초")

    except KeyboardInterrupt:
        logger.info("사용자에 의해 크롤링 중단됨")
    except Exception as e:
        logger.error(f"크롤링 실패: {e}")
    finally:
        # 드라이버 종료
        crawler.close_driver()


if __name__ == "__main__":
    try:
        # 사용 예시:
        # python utils/urlCrowling.py --start-url https://hansung.ac.kr/sites/CSE/index.do --scope cse CSE --max-pages 1000 --delay 1 --timeout 20 --use-requests --verbose
        main()
    except KeyboardInterrupt:
        print("\n크롤링 중단됨")
    except Exception as e:
        print(f"오류: {e}")