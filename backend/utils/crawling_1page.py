from bs4 import BeautifulSoup
import os
import time
import random
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 저장 경로 설정 - 상대 경로로 변경
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "input2", "input")

# User-Agent 목록
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

class Crawler:
    def __init__(self, url):
        self.visited_urls = set()
        self.saved_files = []
        self.saved_attachments = []
        self.delay = 1  # 요청 간 딜레이 (초)
        
        # URL에서 도메인 추출
        parsed_url = urlparse(url)
        self.base_domain = parsed_url.netloc
        domain = parsed_url.netloc
        
        # 오늘 날짜와 도메인으로 폴더명 생성
        date_str = datetime.now().strftime('%y%m%d')
        folder_name = f"{date_str}_{domain}"
        
        # 크롤링 결과 저장할 폴더 경로 생성
        self.output_dir = os.path.join(BASE_DIR, folder_name)
        self.attachment_dir = os.path.join(self.output_dir, "attachments")
        
        # 폴더 생성
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.attachment_dir, exist_ok=True)
        
        print(f"크롤링 결과 저장 경로: {self.output_dir}")
        print(f"첨부 파일 저장 경로: {self.attachment_dir}")
        
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
                
        return links, doc_links
    
    def clean_html(self, html_content):
        """HTML 내용에서 script와 style 태그 및 style 속성, 불필요한 공백 정리"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # script와 style 태그 제거
        for script in soup.find_all(['script', 'style']):
            script.decompose()
        
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

    def crawl_single_page(self, url):
        """단일 페이지만 크롤링하는 함수"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        
        print(f"단일 페이지 크롤링 시작: {url}")
        
        try:
            # Selenium으로 페이지 로드
            self.driver.get(url)
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # 페이지 방문 표시
            self.visited_urls.add(url)
            
            # 페이지 내용 가져오기
            html_content = self.driver.page_source
            
            # 현재 URL 가져오기 (리다이렉션이 있을 수 있음)
            current_url = self.driver.current_url
            
            # Text 파일로 저장 (HTML 태그 포함)
            saved_file = self.save_page_to_text(current_url, html_content, domain)
            
            print(f"페이지 크롤링 성공: {current_url}")
            
            # BeautifulSoup으로 파싱 (문서 링크 추출용)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 링크 추출 (문서 파일만 처리)
            _, doc_links = self.extract_links(soup, current_url)
            
            # 문서 파일 다운로드 처리
            for i, doc_url in enumerate(doc_links):
                if doc_url not in self.visited_urls:
                    doc_progress = f"문서 파일 [{i+1}/{len(doc_links)}]"
                    print(f"{doc_progress} 발견: {doc_url}")
                    file_path = self.document_processor.download_document(doc_url)
                    if file_path:
                        self.saved_attachments.append(file_path)
                    time.sleep(self.delay)
            
            print(f"\n크롤링 완료:")
            print(f"저장된 Text 파일: {len(self.saved_files)}")
            print(f"저장된 문서 파일: {len(self.saved_attachments)}")
            
            return self.saved_files, self.saved_attachments
            
        except Exception as e:
            print(f"페이지 크롤링 실패: {url}, 오류: {str(e)}")
            return [], []

def crawl_main():
    # 크롤링할 URL
    url = "https://hansung.ac.kr/hansung/8385/subview.do?enc=Zm5jdDF8QEB8JTJGYmJzJTJGaGFuc3VuZyUyRjE0MyUyRjI2ODM5MiUyRmFydGNsVmlldy5kbyUzRnBhZ2UlM0QxJTI2c3JjaENvbHVtbiUzRCUyNnNyY2hXcmQlM0QlMjZiYnNDbFNlcSUzRCUyNmJic09wZW5XcmRTZXElM0QlMjZyZ3NCZ25kZVN0ciUzRCUyNnJnc0VuZGRlU3RyJTNEJTI2aXNWaWV3TWluZSUzRGZhbHNlJTI2cGFzc3dvcmQlM0QlMjY%3D"
    
    crawler = Crawler(url=url)
    
    try:
        # 단일 페이지 크롤링
        saved_files, saved_attachments = crawler.crawl_single_page(url)            
        print(f"총 {len(saved_files)}개 text 파일 저장 완료")
        print(f"총 {len(saved_attachments)}개 문서 파일 다운로드 완료")
        return saved_files, saved_attachments
    
    finally:
        crawler.driver.quit() # 크롤러 종료 시 드라이버 닫기 

if __name__ == "__main__":
    crawl_main() 