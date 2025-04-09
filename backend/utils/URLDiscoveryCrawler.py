from bs4 import BeautifulSoup
import os
import time
import random
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 저장 경로 설정
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawling_results")

# User-Agent 목록
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

class URLDiscoveryCrawler:
    def __init__(self, max_pages=100, delay=1):
        self.visited_urls = set()
        self.base_domain = ""
        self.max_pages = max_pages
        self.delay = delay
        
        # Selenium 설정
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)  # 페이지 로드 타임아웃 30초
        
        # 결과 저장용 디렉토리 설정
        os.makedirs(BASE_DIR, exist_ok=True)

    def __del__(self):
        """드라이버 종료"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def is_valid_url(self, url):
        """URL이 유효한지, 같은 도메인인지 확인"""
        parsed = urlparse(url)
        
        # 도메인 체크
        if not parsed.netloc:
            return False
            
        # 같은 도메인인지 확인 (서브도메인 허용)
        return self.base_domain in parsed.netloc
    
    def should_exclude_url(self, url):
        """크롤링에서 제외할 URL 패턴 확인"""
        # 제외할 패턴 목록
        exclude_patterns = [
            '/login', 
            '/logout',
            '/search?',
            'javascript:',
            '#',
            '.pdf',
            '.doc',
            '.docx',
            '.hwp',
            '.xls',
            '.xlsx',
            '.jpg',
            '.jpeg',
            '.png',
            '.gif',
            'mailto:',
            'tel:',
            '/api/',
            '/rss/'
        ]
        
        lower_url = url.lower()
        
        # 제외 패턴 확인
        for pattern in exclude_patterns:
            if pattern in lower_url:
                return True
                
        return False

    def extract_links(self, soup, base_url):
        """페이지에서 링크 추출 (일반 페이지, 문서 파일)"""
        links = set()
        doc_links = set()
        
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            full_url = urljoin(base_url, href)
            
            # 문서 파일 링크인지 확인
            if full_url.lower().endswith(('.pdf', '.docx', '.hwp', '.xls', '.xlsx', '.ppt', '.pptx')):
                doc_links.add(full_url)
            # 일반 URL 추가 (제외 패턴 체크)
            elif self.is_valid_url(full_url) and not self.should_exclude_url(full_url):
                links.add(full_url)
                
        return links, doc_links

    def navigate_to_next_page(self):
        """페이지네이션을 통해 다음 페이지로 이동"""
        try:
            # 다양한 페이지네이션 패턴 확인
            
            # 1. 일반적인 다음 페이지 버튼 검색
            next_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                "a.next, a.nextpage, a[rel='next'], a:contains('다음'), a:contains('Next'), .pagination a[aria-label='Next']")
            
            if not next_buttons:
                # 2. 한성대 사이트의 특정 페이징 클래스 검색
                try:
                    paging_div = self.driver.find_element(By.CLASS_NAME, '_paging')
                    next_button = paging_div.find_element(By.CLASS_NAME, '_listNext')
                    
                    # 클릭하기 전에 페이지 URL 저장
                    before_url = self.driver.current_url
                    
                    # 다음 버튼 클릭 (JavaScript 함수 실행)
                    self.driver.execute_script("arguments[0].click();", next_button)
                    
                    # 페이지 로딩 대기
                    time.sleep(2)
                    
                    # URL 변경 확인
                    if self.driver.current_url != before_url:
                        return True
                        
                except (NoSuchElementException, TimeoutException):
                    pass
                    
            # 3. 숫자 페이징 검색 (현재 페이지 다음 번호 클릭)
            try:
                # 현재 활성화된 페이지 번호 찾기
                active_page = self.driver.find_element(By.CSS_SELECTOR, 
                    ".pagination li.active, .pagination .current, ._paging .active, ._paging ._on")
                
                # 현재 활성화된 페이지의 부모 요소 찾기
                parent = active_page.find_element(By.XPATH, "..")
                
                # 부모 내에서 다음 형제 요소 찾기
                next_sibling = self.driver.execute_script(
                    "return arguments[0].nextElementSibling;", active_page)
                
                if next_sibling:
                    # 클릭 가능한 요소 찾기
                    next_link = next_sibling.find_element(By.TAG_NAME, "a")
                    if next_link:
                        before_url = self.driver.current_url
                        next_link.click()
                        time.sleep(2)
                        if self.driver.current_url != before_url:
                            return True
            except (NoSuchElementException, TimeoutException):
                pass
                
            return False
                
        except Exception as e:
            print(f"다음 페이지 이동 실패: {str(e)}")
            return False

    def discover_urls(self, start_url):
        """URL 발견 단계: 크롤링할 모든 URL을 수집하고 저장"""
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc
        
        # 결과 저장할 집합과 큐 초기화
        all_page_urls = set()
        all_doc_urls = set()
        queue = [start_url]
        visited = set()
        current_page = 0
        
        print(f"URL 발견 단계 시작: {start_url}")
        print(f"기본 도메인: {self.base_domain}")
        print(f"최대 페이지 수: {self.max_pages}")
        
        # URLs 수집 시작
        while queue and current_page < self.max_pages:
            current_url = queue.pop(0)
            
            if current_url in visited:
                continue
            
            # 프로토콜 확인 (http나 https만 처리)
            if not (current_url.startswith('http://') or current_url.startswith('https://')):
                continue
                
            try:
                # 현재 진행 상황 표시
                current_page += 1
                progress = f"[{current_page}/{self.max_pages}]"
                print(f"{progress} URL 발견 중: {current_url}")
                
                # Selenium으로 페이지 로드
                self.driver.get(current_url)
                
                # 페이지 로딩 대기
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                
                # 방문 표시
                visited.add(current_url)
                all_page_urls.add(current_url)
                
                # 현재 URL 가져오기 (리다이렉션 고려)
                current_url = self.driver.current_url
                
                # 페이지 내용 가져오기
                html_content = self.driver.page_source
                
                # BeautifulSoup으로 파싱
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 링크 추출
                links, documents = self.extract_links(soup, current_url)
                
                # 문서 URL 저장
                for doc_url in documents:
                    if doc_url not in all_doc_urls:
                        all_doc_urls.add(doc_url)
                        print(f"{progress} 문서 발견: {doc_url}")
                
                # 페이지네이션 처리
                has_pagination = False
                try:
                    # 다양한 페이지네이션 요소 확인
                    pagination_selectors = [
                        ".pagination", "._paging", ".paging", ".page-navigation",
                        "ul.page", "div.paginate"
                    ]
                    
                    for selector in pagination_selectors:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            has_pagination = True
                            break
                            
                except NoSuchElementException:
                    has_pagination = False
                
                # 페이지네이션이 있는 경우
                if has_pagination:
                    print(f"{progress} 페이지네이션 발견: {current_url}")
                    
                    pagination_page_count = 0
                    max_pagination_pages = 20  # 한 게시판당 최대 페이지 수 제한
                    
                    # 모든 페이지 URL 수집
                    while pagination_page_count < max_pagination_pages:
                        if not self.navigate_to_next_page():
                            print(f"{progress} 더 이상 다음 페이지가 없습니다.")
                            break
                        
                        pagination_page_count += 1
                        time.sleep(self.delay)
                        
                        next_url = self.driver.current_url
                        
                        if next_url in visited:
                            continue
                            
                        if current_page >= self.max_pages:
                            break
                            
                        current_page += 1
                        progress = f"[{current_page}/{self.max_pages}]"
                        print(f"{progress} 페이지네이션 URL 발견 중: {next_url}")
                        
                        visited.add(next_url)
                        all_page_urls.add(next_url)
                        
                        # 새 페이지의 링크 추출
                        html_content = self.driver.page_source
                        soup = BeautifulSoup(html_content, 'html.parser')
                        new_links, new_docs = self.extract_links(soup, next_url)
                        
                        # 문서 URL 저장
                        for doc_url in new_docs:
                            if doc_url not in all_doc_urls:
                                all_doc_urls.add(doc_url)
                                print(f"{progress} 문서 발견: {doc_url}")
                        
                        # 새 링크 큐에 추가
                        for link in new_links:
                            if link not in visited and link not in queue:
                                queue.append(link)
                
                # 일반 페이지의 링크 큐에 추가
                for link in links:
                    if link not in visited and link not in queue:
                        queue.append(link)
                
                # 요청 간 딜레이
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"{progress} URL 발견 실패: {current_url}, 오류: {str(e)}")
        
        # 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        domain_name = self.base_domain.replace('.', '_')
        
        # 도메인별 폴더 생성
        domain_dir = os.path.join(BASE_DIR, domain_name)
        os.makedirs(domain_dir, exist_ok=True)
        
        # URL 목록 저장
        page_urls_file = os.path.join(domain_dir, f"page_urls_{timestamp}.txt")
        doc_urls_file = os.path.join(domain_dir, f"document_urls_{timestamp}.txt")
        
        self._save_urls_to_file(all_page_urls, page_urls_file)
        self._save_urls_to_file(all_doc_urls, doc_urls_file)
        
        # 또한 JSON 형식으로도 저장 (추가 정보 포함)
        json_data = {
            "timestamp": timestamp,
            "base_url": start_url,
            "base_domain": self.base_domain,
            "total_pages_discovered": len(all_page_urls),
            "total_documents_discovered": len(all_doc_urls),
            "page_urls": list(all_page_urls),
            "document_urls": list(all_doc_urls)
        }
        
        json_file = os.path.join(domain_dir, f"crawl_results_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nURL 발견 단계 완료:")
        print(f"발견된 페이지 URL: {len(all_page_urls)}개")
        print(f"발견된 문서 URL: {len(all_doc_urls)}개")
        print(f"결과 JSON 저장: {json_file}")
        print(f"페이지 URL 목록: {page_urls_file}")
        print(f"문서 URL 목록: {doc_urls_file}")
        
        return {
            "page_urls": all_page_urls,
            "doc_urls": all_doc_urls,
            "results_dir": domain_dir,
            "json_file": json_file
        }
    
    def _save_urls_to_file(self, urls, filepath):
        """URL 목록을 파일로 저장"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for url in urls:
                f.write(f"{url}\n")
        print(f"URL 목록 저장 완료: {filepath}")
    
    def analyze_url_patterns(self, urls):
        """수집된 URL의 패턴을 분석"""
        patterns = {}
        domains = {}
        
        for url in urls:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # 도메인 카운트
            if domain in domains:
                domains[domain] += 1
            else:
                domains[domain] = 1
            
            # 경로 패턴 추출
            path = parsed.path
            path_parts = path.strip('/').split('/')
            
            # 패턴화 (숫자를 {id}로 대체)
            pattern_parts = []
            for part in path_parts:
                # 숫자만 있는 부분을 {id}로 대체
                if part.isdigit():
                    pattern_parts.append('{id}')
                else:
                    pattern_parts.append(part)
            
            pattern = '/' + '/'.join(pattern_parts)
            
            if pattern in patterns:
                patterns[pattern] += 1
            else:
                patterns[pattern] = 1
        
        # 결과 정렬
        sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "domains": sorted_domains,
            "patterns": sorted_patterns
        }

# 메인 함수
def main(start_url, max_pages=100):
    crawler = URLDiscoveryCrawler(max_pages=max_pages)
    
    try:
        # URL 발견 단계 실행
        results = crawler.discover_urls(start_url)
        
        # URL 패턴 분석
        print("\nURL 패턴 분석 중...")
        patterns = crawler.analyze_url_patterns(results["page_urls"])
        
        print("\n도메인 분포:")
        for domain, count in patterns["domains"]:
            print(f"  {domain}: {count}개")
        
        print("\n상위 URL 패턴:")
        for i, (pattern, count) in enumerate(patterns["patterns"][:10], 1):
            print(f"  {i}. {pattern}: {count}개")
        
        return results
    
    except Exception as e:
        print(f"크롤링 중 오류 발생: {str(e)}")
        return None
    
    finally:
        crawler.driver.quit()

if __name__ == "__main__":
    TEST_URL = "https://hansung.ac.kr/sites/CSE/index.do"
    MAX_PAGES = 100  # 테스트용으로 수집할 최대 페이지 수
    
    print(f"URL 발견 단계 크롤링 시작: {TEST_URL}")
    results = main(TEST_URL, MAX_PAGES)
    
    if results:
        print("\n크롤링 결과 요약:")
        print(f"발견된 페이지 URL: {len(results['page_urls'])}개")
        print(f"발견된 문서 URL: {len(results['doc_urls'])}개")
        print(f"결과 저장 경로: {results['results_dir']}")