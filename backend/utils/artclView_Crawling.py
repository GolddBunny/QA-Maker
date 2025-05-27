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
from pathlib import Path

# 저장 경로 설정 - 상대 경로로 변경
BASE_DIR = Path(__file__).parent.parent.parent.parent / "data/crawling/20250526_0412_hansung_ac_kr_sites_hansung/artclView_Crawling"

# User-Agent 목록
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

class Crawler:
    def __init__(self, urls=None, output_base_dir=None):
        self.visited_urls = set()
        self.saved_files = []
        self.saved_attachments = []
        self.delay = 1  # 요청 간 딜레이 (초)
        self.urls_to_crawl = urls or []
        self.curriculum_counter = 0  # curriculum 페이지 카운터
        
        # 첫 번째 URL에서 도메인 추출 (모든 URL이 같은 도메인이라고 가정)
        if self.urls_to_crawl:
            parsed_url = urlparse(self.urls_to_crawl[0])
            self.base_domain = parsed_url.netloc
            domain = parsed_url.netloc
            print(f"도메인: {self.base_domain}")
        else:
            self.base_domain = "hansung.ac.kr"
            domain = "hansung.ac.kr"
        
        # 저장 경로 설정
        if output_base_dir is None:
            # 기본 경로 사용 (기존 로직)
            date_str = datetime.now().strftime('%y%m%d%H%M')
            folder_name = f"{date_str}_{domain}_multiple_pages"
            self.output_dir = os.path.join(BASE_DIR, folder_name)
        else:
            # 외부에서 지정한 경로 사용
            timestamp = datetime.now().strftime('%y%m%d%H%M')
            folder_name = f"{timestamp}_{domain}_multiple_pages"
            self.output_dir = os.path.join(output_base_dir, folder_name)
        
        self.attachment_dir = os.path.join(self.output_dir, "attachments")
        
        # 폴더 생성
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.attachment_dir, exist_ok=True)
        
        print(f"크롤링 결과 저장 경로: {self.output_dir}")
        print(f"첨부 파일 저장 경로: {self.attachment_dir}")
        print(f"크롤링할 URL 개수: {len(self.urls_to_crawl)}")
        
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
    
    def extract_view_util_metadata(self, soup):
        """view-util 태그에서 분류, 작성일, 작성자 정보 추출"""
        metadata = {
            'category': '',
            'date': '',
            'author': ''
        }
        
        # view-util 클래스를 가진 div 태그 찾기
        view_util = soup.find('div', class_='view-util')
        if not view_util:
            return metadata
        
        # dl 태그들을 찾아서 정보 추출
        dl_tags = view_util.find_all('dl')
        
        for dl in dl_tags:
            dt = dl.find('dt')
            dd = dl.find('dd')
            
            if dt and dd:
                dt_text = dt.get_text().strip()
                dd_text = dd.get_text().strip()
                
                # 분류 정보 추출
                if '분류' in dt_text:
                    metadata['category'] = dd_text
                
                # 작성일 정보 추출
                elif '작성일' in dt_text:
                    metadata['date'] = dd_text
                
                # 작성자 정보 추출
                elif '작성자' in dt_text:
                    metadata['author'] = dd_text
        
        return metadata

    def html_to_markdown(self, html_content):
        """HTML 내용을 마크다운 형식으로 변환"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # view-util 메타데이터 추출
        metadata = self.extract_view_util_metadata(soup)
        
        # 스크립트, 스타일, 헤드 태그 제거
        for tag in soup.find_all(['script', 'style', 'head', 'meta', 'link', 'iframe']):
            tag.decompose()
            
        # 페이지 제목 찾기
        title = ""
        if soup.find('h2', class_='view-title'):
            title = soup.find('h2', class_='view-title').get_text().strip()
        elif soup.title:
            title = soup.title.string.strip() if soup.title.string else ""
        
        # 중복 내용 방지를 위한 처리된 텍스트 집합
        processed_texts = set()
        content_parts = []
        
        # 주요 콘텐츠 영역 찾기
        main_contents = []
        
        # 주요 콘텐츠 영역 찾기
        if soup.find('div', class_='view-con'):
            main_contents.append(soup.find('div', class_='view-con'))
        elif soup.find('div', class_='contents'):
            main_contents.append(soup.find('div', class_='contents'))
        elif soup.find('article'):
            main_contents.append(soup.find('article'))
        else:
            # 특정 클래스가 없으면 body에서 주요 div 태그 찾기
            for div in soup.find_all('div', class_=True):
                if 'content' in div.get('class', [''])[0].lower() or 'article' in div.get('class', [''])[0].lower():
                    main_contents.append(div)
        
        # 주요 콘텐츠 영역이 없으면 body 전체 사용
        if not main_contents:
            main_contents = [soup.body] if soup.body else [soup]
        
        # 내용 추출
        for main_content in main_contents:
            # 제목 태그 추출
            for heading in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                heading_text = heading.get_text().strip()
                if heading_text and heading_text not in processed_texts:
                    content_parts.append(f"## {heading_text}")
                    processed_texts.add(heading_text)
            
            # 단락 추출
            for p in main_content.find_all('p'):
                p_text = p.get_text().strip()
                if p_text and p_text not in processed_texts and len(p_text) > 1:
                    content_parts.append(p_text)
                    processed_texts.add(p_text)
        
        # 내용이 없으면 다른 방식으로 추출 시도
        if not content_parts:
            for elem in soup.find_all(['p', 'div']):
                if elem.parent.name not in ['script', 'style'] and not elem.find_all('div'):
                    text = elem.get_text().strip()
                    if text and text not in processed_texts and len(text) > 1:
                        content_parts.append(text)
                        processed_texts.add(text)
        
        # 테이블 추출 및 처리 - 테이블은 별도로 마크다운으로 변환
        tables_markdown = ""
        tables = []
        for table in soup.find_all('table'):
            # 이미 처리한 동일 구조의 테이블은 제외
            table_html = str(table)
            if table_html not in processed_texts:
                processed_texts.add(table_html)
                tables.append(table)
        
        # 테이블 마크다운 변환
        if tables:
            tables_content = []
            for i, table in enumerate(tables):
                table_title = self.extract_table_title(table, i)
                markdown_table = self.convert_table_to_markdown(table)
                if markdown_table:
                    tables_content.append(f"### {table_title}\n\n{markdown_table}")
            
            if tables_content:
                tables_markdown = "\n\n".join(tables_content)
        
        # 최종 내용 조합
        content = "\n\n".join(content_parts)
        
        # 테이블 내용이 있으면 추가
        if tables_markdown:
            if content:
                content = f"{content}\n\n{tables_markdown}"
            else:
                content = tables_markdown
        
        return title, content, metadata

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
        
        # 헤더가 없는 경우 모든 행을 일반 데이터로 처리
        rows = table.find_all('tr')
        if rows:
            # 모든 행의 열 수 중 최대값 찾기
            max_cols = 0
            for row in rows:
                cols = len(row.find_all(['td', 'th']))
                max_cols = max(max_cols, cols)
            
            if max_cols > 0:
                # 헤더 행(빈 헤더) 추가
                markdown_table.append("| " + " | ".join([""] * max_cols) + " |")
                # 구분선 추가
                markdown_table.append("| " + " | ".join(["---"] * max_cols) + " |")
                
                # 데이터 행 추가
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        row_data = []
                        for cell in cells:
                            cell_text = cell.get_text().strip()
                            cell_text = re.sub(r'\s+', ' ', cell_text)
                            row_data.append(cell_text)
                        
                        # 열 수 맞추기
                        while len(row_data) < max_cols:
                            row_data.append("")
                        
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
                
                # 테이블 제목과 내용 추가
                markdown_tables.append(f"\n### {table_title}\n")
                markdown_tables.append(markdown_table)
        
        if markdown_tables:
            return "\n".join(markdown_tables)
        return ""

    def extract_attachments_info(self, soup, base_url):
        """페이지에서 첨부파일 정보 추출"""
        attachments = []
        
        # 일반적인 첨부파일 링크 패턴들 확인
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            full_url = urljoin(base_url, href)
            
            # 파일 확장자 확인
            if self.is_document_url(full_url):
                # 링크 텍스트에서 파일명 추출
                link_text = anchor.get_text().strip()
                if not link_text:
                    # 링크 텍스트가 없으면 URL에서 파일명 추출
                    link_text = full_url.split('/')[-1]
                
                attachments.append({
                    'name': link_text,
                    'url': full_url
                })
        
        # 첨부파일 영역에서 추가 정보 확인
        attach_sections = soup.find_all(['div', 'section'], class_=lambda x: x and ('attach' in x.lower() or 'file' in x.lower()))
        for section in attach_sections:
            for anchor in section.find_all('a', href=True):
                href = anchor['href']
                full_url = urljoin(base_url, href)
                link_text = anchor.get_text().strip()
                
                if link_text and not any(att['name'] == link_text for att in attachments):
                    attachments.append({
                        'name': link_text,
                        'url': full_url
                    })
        
        return attachments

    def clean_filename(self, filename):
        """파일명에서 사용할 수 없는 문자 제거"""
        # Windows/Mac/Linux에서 사용할 수 없는 문자들 제거
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 연속된 공백을 하나로 줄이기
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        # 파일명이 너무 길면 자르기 (확장자 포함 최대 100자)
        if len(filename) > 96:  # .txt 확장자 4자 고려
            filename = filename[:96]
        
        return filename

    def check_page_title(self, html_content):
        """페이지 제목이 Alert 500인지 확인"""
        soup = BeautifulSoup(html_content, 'html.parser')
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            title_text = title_tag.string.strip()
            return title_text == "Alert 500"
        return False

    def save_page_to_text(self, url, html_content, domain, attachments_info=None):
        """크롤링한 페이지를 텍스트 파일로 저장"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # HTML을 마크다운으로 변환
        title, content, metadata = self.html_to_markdown(html_content)
        
        # 파일명을 title 기반으로 생성
        if title and title.strip():
            filename = self.clean_filename(title.strip())
        else:
            # 제목이 없는 경우
            if 'curriculum' in url.lower():
                # curriculum URL인 경우 특별한 넘버링
                self.curriculum_counter += 1
                filename = f"curriculum_{self.curriculum_counter}"
            else:
                # 일반적인 URL 기반 파일명 생성
                parsed_url = urlparse(url)
                path = parsed_url.path.strip('/')
                if path:
                    path = path.replace('/', '_')
                    if path.endswith('.html'):
                        path = path[:-5]
                    filename = f"{domain}_{path}"
                else:
                    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                    filename = f"{domain}_{timestamp}"
        
        filename = f"{filename}.txt"
        file_path = os.path.join(self.output_dir, filename)
        
        # 파일명 중복 처리
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            name_without_ext = original_path[:-4]  # .txt 제거
            file_path = f"{name_without_ext}_{counter}.txt"
            counter += 1
        
        # 첨부파일 정보 추가
        attachments_text = ""
        if attachments_info:
            attachments_text = "\n\n## 첨부파일\n\n"
            for i, attachment in enumerate(attachments_info, 1):
                attachments_text += f"{i}. 첨부파일: {attachment['name']} 함께 제공됨\n"
                attachments_text += f"   - URL: {attachment['url']}\n"
        
        # 메타데이터 정보 추가
        metadata_text = ""
        if metadata and any(metadata.values()):
            metadata_text = "\n\n## 메타데이터\n\n"
            if metadata['category']:
                metadata_text += f"분류: {metadata['category']}\n"
            if metadata['date']:
                metadata_text += f"작성일: {metadata['date']}\n"
            if metadata['author']:
                metadata_text += f"작성자: {metadata['author']}\n"
        
        # 마크다운 형식으로 파일 내용 구성
        text_content = f"""Title: {title}

URL Source: {url}{metadata_text}

Markdown Content:

{content}{attachments_text}
"""
        
        # 텍스트 파일로 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        print(f"텍스트 파일 저장 완료: {file_path}")
            
        self.saved_files.append(file_path)
        return file_path

    def crawl_single_page(self, url, progress_info=""):
        """단일 페이지만 크롤링하는 함수"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('.', '_')
        
        print(f"{progress_info} 페이지 크롤링 시작: {url}")
        
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
            
            # Alert 500 페이지인지 확인
            if self.check_page_title(html_content):
                print(f"{progress_info} Alert 500 페이지 감지 - 크롤링 건너뜀: {url}")
                return None
            
            # 현재 URL 가져오기 (리다이렉션이 있을 수 있음)
            current_url = self.driver.current_url
            
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 첨부파일 정보 추출
            attachments_info = self.extract_attachments_info(soup, current_url)
            
            # Text 파일로 저장 (마크다운 형식, 첨부파일 정보 포함)
            saved_file = self.save_page_to_text(current_url, html_content, domain, attachments_info)
            
            print(f"{progress_info} 페이지 크롤링 성공: {current_url}")
            if attachments_info:
                print(f"  └─ 첨부파일 {len(attachments_info)}개 발견")
            
            return saved_file
            
        except Exception as e:
            print(f"{progress_info} 페이지 크롤링 실패: {url}, 오류: {str(e)}")
            return None

    def crawl_multiple_pages(self):
        """여러 페이지를 순차적으로 크롤링하는 함수"""
        if not self.urls_to_crawl:
            print("크롤링할 URL이 없습니다.")
            return [], []
        
        print(f"\n=== 총 {len(self.urls_to_crawl)}개 페이지 크롤링 시작 ===")
        
        success_count = 0
        failed_count = 0
        
        for i, url in enumerate(self.urls_to_crawl, 1):
            progress_info = f"[{i}/{len(self.urls_to_crawl)}]"
            
            try:
                saved_file = self.crawl_single_page(url, progress_info)
                if saved_file:
                    success_count += 1
                else:
                    failed_count += 1
                
                # 요청 간 딜레이
                if i < len(self.urls_to_crawl):  # 마지막이 아니면 딜레이
                    time.sleep(self.delay)
                    
            except Exception as e:
                print(f"{progress_info} 예외 발생: {str(e)}")
                failed_count += 1
                
        print(f"\n=== 크롤링 완료 ===")
        print(f"성공: {success_count}개")
        print(f"실패: {failed_count}개") 
        print(f"총 저장된 파일: {len(self.saved_files)}개")
        
        return self.saved_files, self.saved_attachments

def read_urls_from_file(file_path):
    """텍스트 파일에서 URL 리스트를 읽어오는 함수"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]
        return urls
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return []
    except Exception as e:
        print(f"파일 읽기 오류: {str(e)}")
        return []

def filter_urls(urls, patterns):
    """URL 리스트에서 특정 패턴이 포함된 URL만 필터링하는 함수"""
    filtered_urls = []
    for url in urls:
        if any(pattern in url for pattern in patterns):
            filtered_urls.append(url)
    return filtered_urls

def crawl_main(test_mode=False, test_limit=5):
    # URL 리스트 파일 경로
    url_file_path = Path(__file__).parent.parent.parent.parent / "data/crawling/20250526_0412_hansung_ac_kr_sites_hansung/pages_urls_20250526_0412.txt"
    
    # 파일에서 URL 리스트 읽기
    all_urls = read_urls_from_file(url_file_path)
    
    if not all_urls:
        print("URL 리스트를 읽을 수 없습니다.")
        return [], []
    
    print(f"총 {len(all_urls)}개의 URL을 읽었습니다.")
    
    # artclView.do 또는 artclList.do가 포함된 URL만 필터링
    target_patterns = ['artclView.do', 'artclList.do']
    filtered_urls = filter_urls(all_urls, target_patterns)
    
    print(f"필터링 후 {len(filtered_urls)}개의 URL이 선택되었습니다.")
    
    if not filtered_urls:
        print("크롤링할 URL이 없습니다.")
        return [], []
    
    # 중복 제거
    unique_urls = list(set(filtered_urls))
    print(f"중복 제거 후 {len(unique_urls)}개의 URL이 남았습니다.")
    
    # 테스트 모드면 URL 개수 제한
    if test_mode:
        unique_urls = unique_urls[:test_limit]
        print(f"테스트 모드: {len(unique_urls)}개 URL만 크롤링합니다.")
    
    # 크롤러 생성 및 실행
    crawler = Crawler(urls=unique_urls)
    
    try:
        # 여러 페이지 크롤링
        saved_files, saved_attachments = crawler.crawl_multiple_pages()
        print(f"총 {len(saved_files)}개 text 파일 저장 완료")
        print(f"총 {len(saved_attachments)}개 문서 파일 다운로드 완료")
        return saved_files, saved_attachments
    
    finally:
        crawler.driver.quit() # 크롤러 종료 시 드라이버 닫기 

if __name__ == "__main__":
    # 테스트를 위해서는 다음과 같이 실행:
    # crawl_main(test_mode=True, test_limit=3)
    # 전체 크롤링을 위해서는:
    crawl_main() 