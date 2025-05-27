from bs4 import BeautifulSoup
import os
import time
import random
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime
#from documents import DocumentProcessor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 저장 경로 설정
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "input")

# User-Agent 목록
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

class Crawler:
    def __init__(self, max_pages, url, page_id):
        self.visited_urls = set()
        self.queue = []
        self.base_domain = ""
        self.saved_files = []
        self.saved_attachments = []
        self.max_pages = max_pages  # 매개변수로 max_pages 받기
        self.delay = 1  # 요청 간 딜레이 (초)
        self.current_page = 0  # 현재 크롤링 중인 페이지 번호
        
        # URL에서 도메인 추출
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # 오늘 날짜와 도메인으로 폴더명 생성
        date_str = datetime.now().strftime('%y%m%d')
        folder_name = f"{date_str}_{domain}"
        
        # 크롤링 결과 저장할 폴더 경로 생성
        #self.output_dir = os.path.join(BASE_DIR, folder_name)
        self.output_dir = os.path.join(BASE_DIR, page_id, "input")
        #self.attachment_dir = os.path.join(self.output_dir, "attachments")
        
        # 폴더 생성
        os.makedirs(self.output_dir, exist_ok=True)
        #os.makedirs(self.attachment_dir, exist_ok=True)
        
        print(f"크롤링 결과 저장 경로: {self.output_dir}")
        #print(f"첨부 파일 저장 경로: {self.attachment_dir}")
        
        #self.document_processor = DocumentProcessor(self.output_dir, self.attachment_dir)
        
        # Selenium 설정
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30) # 페이지 로드 타임아웃 30초

    def __del__(self):
        """드라이버 종료"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def get_random_user_agent(self):
        return random.choice(USER_AGENTS)

    def is_valid_url(self, url):
        """URL이 유효한지, 같은 도메인인지 확인"""
        parsed = urlparse(url)
        return bool(parsed.netloc) and parsed.netloc == self.base_domain

    def is_document_url(self, url):
        """URL이 PDF, DOCX, HWP 파일인지 확인"""
        lower_url = url.lower()
        return lower_url.endswith('.pdf') or lower_url.endswith('.docx') or lower_url.endswith('.hwp')

    def extract_links(self, soup, base_url):
        """페이지에서 링크 추출 (일반 페이지, 문서 파일)"""
        links = set()
        doc_links = set()
        
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            full_url = urljoin(base_url, href)
            
            # 문서 파일 링크인지 확인
            if self.is_document_url(full_url):
                doc_links.add(full_url)
            # 같은 도메인에 속하는 일반 URL 추가
            elif self.is_valid_url(full_url) and full_url not in self.visited_urls:
                links.add(full_url)
                
        return links, doc_links
    
    def clean_html(self, html_content):
        """HTML 내용에서 script와 style 태그 및 style 속성, 불필요한 공백 정리"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # script와 style 태그 제거
        for script in soup.find_all(['script', 'style']):
            script.decompose()
        
        # # style 속성이 있는 빈 div 태그 제거
        # for tag in soup.find_all('div', style=True):
        #     if len(tag.contents) == 0 and not tag.get_text(strip=True) and not tag.attrs.get('id') and not tag.attrs.get('class'):
        #         tag.decompose()
        
        # 남아있는 태그의 style 속성 제거
        for tag in soup.find_all(style=True):
            del tag['style']
                
        html_str = str(soup) # HTML을 문자열로 변환
        html_str = re.sub(r'\n', '', html_str) # 모든 줄바꿈 제거
        html_str = re.sub(r'[ \t]+', ' ', html_str) # 연속된 공백 문자를 하나로 줄이기
        html_str = re.sub(r'>\s+<', '><', html_str) # 태그 사이의 불필요한 공백 제거
        html_str = re.sub(r'^\s+|\s+$', '', html_str, flags=re.MULTILINE) # 줄 시작과 끝의 공백 제거
        html_str = re.sub(r'\n{2,}', '\n', html_str) # 연속된 빈 줄 제거 (한 줄만 남김)
        
        return html_str

    def convert_table_to_markdown(self, table):
        """HTML 테이블을 마크다운 테이블로 변환"""
        markdown_table = []
        
        # 테이블 헤더 찾기 (tr 태그 중 첫 번째 또는 thead 내부 tr)
        headers = []
        thead = table.find('thead')
        if thead:
            header_row = thead.find('tr')
        else:
            header_row = table.find('tr')
        
        if header_row:
            # th 태그가 없으면 td 태그 사용
            header_cells = header_row.find_all(['th', 'td'])
            for cell in header_cells:
                # 셀 내용에서 불필요한 공백 제거
                header_text = cell.get_text().strip()
                # 줄바꿈을 공백으로 대체
                header_text = re.sub(r'\s+', ' ', header_text)
                headers.append(header_text)
            
            if headers:
                # 헤더 행 추가
                markdown_table.append("| " + " | ".join(headers) + " |")
                # 구분선 추가
                markdown_table.append("| " + " | ".join(["---"] * len(headers)) + " |")                
                # 데이터 행 추가
                tbody = table.find('tbody')
                rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        row_data = []
                        for cell in cells:
                            # 셀 내용에서 불필요한 공백 제거
                            cell_text = cell.get_text().strip()
                            # 줄바꿈을 공백으로 대체
                            cell_text = re.sub(r'\s+', ' ', cell_text)
                            row_data.append(cell_text)
                        
                        # 열 수가 헤더와 다를 경우 빈 셀로 채우기
                        while len(row_data) < len(headers):
                            row_data.append("")
                        
                        # 헤더보다 열이 더 많을 경우 잘라내기
                        row_data = row_data[:len(headers)]
                        
                        markdown_table.append("| " + " | ".join(row_data) + " |")                
                return "\n".join(markdown_table)        
        return ""

    def extract_table_title(self, table, index):
        """테이블 제목 찾기"""
        # 1. 테이블 바로 앞에 있는 caption 태그 확인
        caption = table.find('caption')
        if caption and caption.get_text().strip():
            return caption.get_text().strip()
                
        # 2. 테이블 바로 위에 있는 가장 가까운 헤딩 태그 확인
        current = table
        heading = None       
        # 이전 테이블까지만 검색 (다른 테이블과 헤딩을 공유하지 않도록)
        while current:
            prev = current.find_previous_sibling()
            if not prev:
                # 부모로 올라가서 부모의 이전 형제 요소 검색
                parent = current.parent
                if parent and parent.name != 'body':
                    current = parent
                    continue
                else:
                    break                   
            
            # 테이블을 만나면 중단 (다른 테이블의 헤딩을 가져오지 않기 위함)
            if prev.name == 'table':
                break

            # 헤딩 태그인지 확인
            if prev.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                heading = prev
                break                
            current = prev
        
        if heading and heading.get_text().strip():
            return heading.get_text().strip()
        
        # 3. 테이블에 id나 class 속성이 있는지 확인
        table_id = table.get('id', '')
        if table_id:
            return f"테이블 ID: {table_id}"    
        table_class = table.get('class', '')
        if table_class:
            return f"테이블 클래스: {' '.join(table_class)}"
        
        # 4. 테이블 내의 첫 번째 행에서 의미 있는 제목을 찾을 수 있는지
        first_row = table.find('tr')
        if first_row:
            first_cell = first_row.find(['th', 'td'])
            if first_cell and first_cell.get_text().strip():
                # 첫 셀이 제목처럼 보이면 (짧고 명확한 텍스트)
                text = first_cell.get_text().strip()
                if len(text) < 50 and not text.isdigit():
                    return f"{text} 관련 표"

        # 식별 가능한 이름이 없으면 인덱스를 포함한 기본값 반환
        return f"테이블 {index+1}"

    def extract_tables_as_markdown(self, html_content):
        """HTML에서 모든 테이블을 찾아 마크다운으로 변환"""
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table')
        
        if not tables:
            return ""
        
        markdown_tables = []
        markdown_tables.append("\n## 테이블 마크다운 변환 결과")
        
        # 이미 사용된 테이블 이름을 추적
        used_titles = {}
        
        for i, table in enumerate(tables):
            markdown_table = self.convert_table_to_markdown(table)
            if markdown_table:
                # 테이블의 실제 제목 찾기
                table_title = self.extract_table_title(table, i)
                
                # 중복된 이름이 있으면 번호 추가
                if table_title in used_titles:
                    used_titles[table_title] += 1
                    table_title = f"{table_title} ({used_titles[table_title]})"
                else:
                    used_titles[table_title] = 1
                    
                markdown_tables.append(f"### {table_title}")
                markdown_tables.append(markdown_table)
        return "\n".join(markdown_tables)

    def save_page_to_text(self, url, html_content, domain):
        """크롤링한 페이지를 텍스트 파일로 저장"""
        os.makedirs(self.output_dir, exist_ok=True)

        # clean_html 함수를 사용하여 HTML 내용 정리
        cleaned_html = self.clean_html(html_content)
        
        # URL에서 파일명 생성
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')
        
        if path:
            # 경로가 있으면 경로를 기반으로 파일명 생성
            path = path.replace('/', '_')
            if path.endswith('.html'):
                path = path[:-5]
            filename = f"{domain}_{path}.txt"
        else:
            # 경로가 없으면 (홈페이지 등) 타임스탬프 사용
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{domain}_{timestamp}.txt"
        
        # 파일명 처리
        if len(filename) > 100:
            filename = filename[:100] + '.txt'
        
        file_path = os.path.join(self.output_dir, filename)
        
        # 파일명 중복 처리
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            file_path = original_path.replace('.txt', f'_{counter}.txt')
            counter += 1
        
        # 페이지 제목 찾기
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.title.string if soup.title else "페이지 정보"
        
        # 테이블 마크다운 변환 결과 생성 추가
        markdown_tables = self.extract_tables_as_markdown(html_content)
        
        # 텍스트 파일 구조 생성
        text_content = f"""title: {title}\nURL: {url}\ntext: "{cleaned_html}"{markdown_tables}
        """
        # 텍스트 파일로 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        print(f"텍스트 파일 저장 완료: {file_path}")
            
        self.saved_files.append(file_path)
        return file_path

    def navigate_to_next_page(self):
        """페이지네이션을 통해 다음 페이지로 이동"""
        try:
            # 페이징 영역 찾기 (요소가 있는지 확인)
            paging_div = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, '_paging'))
            )
            
            # 페이지 상태 정보 직접 찾기
            page_state = paging_div.find_element(By.CLASS_NAME, '_pageState')
            
            # 현재 페이지와 총 페이지 요소 찾기
            current_page_elem = page_state.find_element(By.CLASS_NAME, '_curPage')
            total_page_elem = page_state.find_element(By.CLASS_NAME, '_totPage')
            
            # 디버깅용 출력
            print(f"현재 페이지 요소 내용: '{current_page_elem.text}'")
            print(f"총 페이지 요소 내용: '{total_page_elem.text}'")
            
            # 페이지 번호 텍스트 가져오기
            current_page_text = current_page_elem.text.strip()
            total_page_text = total_page_elem.text.strip()
            
            # 페이지 번호가 비어있는지 확인
            if not current_page_text or not total_page_text:
                # 다른 방법으로 시도: get_attribute('innerText') 사용
                current_page_text = current_page_elem.get_attribute('innerText').strip()
                total_page_text = total_page_elem.get_attribute('innerText').strip()
                
                print(f"현재 페이지네이션: {current_page_text}")
                print(f"총 페이지네이션: {total_page_text}")
                
                if not current_page_text or not total_page_text:
                    print("페이지 번호 정보를 가져올 수 없습니다.")
                    return False
            
            # 정수로 변환
            try:
                current_page = int(current_page_text)
                total_pages = int(total_page_text)
            except ValueError:
                print(f"페이지 번호 변환 실패: 현재={current_page_text}, 총={total_page_text}")
                return False
            
            print(f"현재 페이지: {current_page}, 총 페이지: {total_pages}")
            
            # 다음 페이지가 있는지 확인
            if current_page < total_pages:
                # 다음 버튼 찾기
                next_button = paging_div.find_element(By.CLASS_NAME, '_listNext')                
                # 클릭하기 전에 페이지 URL 저장
                before_url = self.driver.current_url                
                # 다음 버튼 클릭 (JavaScript 함수 실행)
                self.driver.execute_script("arguments[0].click();", next_button)                
                # 페이지 로딩 대기
                time.sleep(2)              
                # 페이지 변경 확인 (URL 또는 페이지 번호)
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.current_url != before_url
                    )
                    print(f"페이지 {current_page} → {current_page + 1} 이동 성공")
                    return True
                except TimeoutException:
                    # URL이 변경되지 않았으면 페이지 번호 확인
                    try:
                        new_page_elem = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CLASS_NAME, '_curPage'))
                        )
                        new_page = int(new_page_elem.text.strip() or '0')
                        if new_page > current_page:
                            print(f"페이지 {current_page} → {new_page} 이동 성공")
                            return True
                        else:
                            print("페이지 이동이 확인되지 않았습니다.")
                            return False
                    except (TimeoutException, ValueError):
                        print("페이지 이동 후 페이지 번호를 확인할 수 없습니다.")
                        return False
            else:
                print("마지막 페이지에 도달했습니다.")
                return False                
        except (TimeoutException, NoSuchElementException) as e:
            print(f"다음 페이지로 이동 실패: {str(e)}")
            return False

    def crawl_combined(self, start_url):
        """페이지네이션 + 큐 기반 크롤링 결합"""
        parsed_url = urlparse(start_url)
        self.base_domain = parsed_url.netloc
        self.current_page = 0
        
        # 시작 URL을 큐에 추가
        self.queue = [start_url]
        self.visited_urls = set()
        
        print(f"통합 크롤링 시작: {start_url}")
        print(f"최대 페이지 수: {self.max_pages}")
        
        while self.queue and self.current_page < self.max_pages:
            current_url = self.queue.pop(0)
            
            if current_url in self.visited_urls:
                continue
                
            try:
                # 현재 진행 상황 표시
                self.current_page += 1
                progress = f"[{self.current_page}/{self.max_pages}]"
                print(f"{progress} 페이지 크롤링 중: {current_url}")
                
                # Selenium으로 페이지 로드
                self.driver.get(current_url)
                
                # 페이지 로딩 대기
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                
                # 페이지 방문 표시
                self.visited_urls.add(current_url)
                
                # 페이지 내용 가져오기
                html_content = self.driver.page_source
                
                # 현재 URL 가져오기 (리다이렉션이 있을 수 있음)
                current_url = self.driver.current_url
                
                # Text 파일로 저장 (HTML 태그 포함)
                domain = self.base_domain.replace('.', '_')
                saved_file = self.save_page_to_text(current_url, html_content, domain)
                
                print(f"{progress} 페이지 크롤링 성공: {current_url}")
                
                # BeautifulSoup으로 파싱 (링크 추출용)
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 링크 추출
                links, doc_links = self.extract_links(soup, current_url)
                
                # # 문서 파일 다운로드 처리
                # for i, doc_url in enumerate(doc_links):
                #     if doc_url not in self.visited_urls:
                #         doc_progress = f"{progress} 문서 파일 [{i+1}/{len(doc_links)}]"
                #         print(f"{doc_progress} 발견: {doc_url}")
                #         file_path = self.document_processor.download_document(doc_url)
                #         if file_path:
                #             self.saved_attachments.append(file_path)
                #         time.sleep(self.delay)
                
                # 페이지네이션 확인 - 현재 페이지에서 다음 페이지가 있는지 검사
                is_pagination_page = False
                try:
                    # 페이징 영역 찾기 (요소가 있는지 확인)
                    paging_div = self.driver.find_element(By.CLASS_NAME, '_paging')
                    is_pagination_page = True
                except NoSuchElementException:
                    is_pagination_page = False
                
                # 페이지네이션이 있는 페이지라면 다음 페이지 우선 처리
                if is_pagination_page:
                    print(f"{progress} 페이지네이션 발견: {current_url}")
                    
                    # 현재 페이지 저장
                    temp_queue = self.queue.copy()
                    self.queue = []
                    
                    # 페이지네이션 순서대로 크롤링
                    while self.current_page < self.max_pages:
                        if not self.navigate_to_next_page():
                            #print("더 이상 페이지가 없습니다.")
                            break
                        
                        # 페이지 이동 후 잠시 대기
                        time.sleep(self.delay)
                        
                        # 현재 URL 가져오기
                        next_url = self.driver.current_url
                        
                        if next_url in self.visited_urls:
                            continue
                            
                        # 현재 진행 상황 표시
                        self.current_page += 1
                        if self.current_page > self.max_pages:
                            break
                            
                        progress = f"[{self.current_page}/{self.max_pages}]"
                        print(f"{progress} 페이지네이션 페이지 크롤링 중: {next_url}")                        
                        # 페이지 방문 표시
                        self.visited_urls.add(next_url)                        
                        # 페이지 내용 가져오기
                        html_content = self.driver.page_source                        
                        # Text 파일로 저장
                        saved_file = self.save_page_to_text(next_url, html_content, domain)                        
                        # 링크 추출
                        soup = BeautifulSoup(html_content, 'html.parser')
                        new_links, new_doc_links = self.extract_links(soup, next_url)
                        
                        # 문서 파일 처리
                        # for i, doc_url in enumerate(new_doc_links):
                        #     if doc_url not in self.visited_urls:
                        #         doc_progress = f"{progress} 문서 파일 [{i+1}/{len(new_doc_links)}]"
                        #         # print(f"{doc_progress} 발견: {doc_url}")
                        #         file_path = self.document_processor.download_document(doc_url)
                        #         if file_path:
                        #             self.saved_attachments.append(file_path)
                        #         time.sleep(self.delay)
                        
                        # 새 링크 큐에 추가
                        for link in new_links:
                            if link not in self.visited_urls and link not in temp_queue and link not in self.queue:
                                temp_queue.append(link)
                    
                    # 원래 큐 복원 (새로 발견된 링크 포함)
                    self.queue = temp_queue
                else:
                    # 페이지네이션이 없는 일반 페이지라면 링크 큐에 추가
                    for link in links:
                        if link not in self.visited_urls and link not in self.queue:
                            self.queue.append(link)
                
                # 요청 간 딜레이
                time.sleep(self.delay)
                
            except Exception as e:
                print(f"{progress} 페이지 크롤링 실패: {current_url}, 오류: {str(e)}")
        
        print(f"\n크롤링 완료:")
        print(f"처리된 페이지: {len(self.visited_urls)}")
        print(f"저장된 Text 파일: {len(self.saved_files)}")
        print(f"저장된 문서 파일: {len(self.saved_attachments)}")
        
        return self.saved_files, self.saved_attachments

def crawl_main(url, page_id, max_pages=2): # 최대 페이지 수 지정
    crawler = Crawler(max_pages=max_pages, url=url, page_id=page_id)
    
    try:
        # 통합 크롤링
        saved_files, saved_attachments = crawler.crawl_combined(url)   
        print(f"총 {len(saved_files)}개 text 파일 저장 완료")
        print(f"총 {len(saved_attachments)}개 문서 파일 다운로드 완료")
        return saved_files, saved_attachments
    
    finally:
        crawler.driver.quit() # 크롤러 종료 시 드라이버 닫기