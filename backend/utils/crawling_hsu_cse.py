import os
import time
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from convert2txt import convert2txt

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', './chromedriver')
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# 게시글(Article)이 있는 페이지 크롤링
def scrape_all_pages(driver, url, folder_path):
    driver.get(url)
    time.sleep(2)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table = soup.find('table')
    if table and table.find('a'):
        print(f"[INFO] 게시글 페이지 감지: {url}")
        # 네비게이션 페이지 수 찾기
        try:
            # _totPage 요소의 텍스트 값 가져오기
            tot_page_element = driver.find_element(By.CLASS_NAME, "_totPage")
            total_pages_text = tot_page_element.text.strip()

            # 값이 없으면 JavaScript로 시도
            if not total_pages_text:
                total_pages_text = driver.execute_script("return document.querySelector('._totPage')?.innerText;").strip()
            if not total_pages_text:
                pagination_links = driver.find_elements(By.CSS_SELECTOR, 'a.page-link')  # 페이지네이션 링크
                total_pages = int(pagination_links[-1].text)  # 마지막 링크에서 페이지 번호 추출
            # 최종적으로 `int()` 변환
            total_pages = int(total_pages_text)
            print(f"총 페이지 수: {total_pages}")  # total_pages 값 확인
        except Exception as e:
            print(f"페이지 로드 실패: {e}")
            return

        # 각 페이지에서 게시글 링크를 크롤링하여 처리
        for page in range(1, total_pages + 1):  # 1부터 마지막 페이지까지 반복
            print(f'Scraping page {page}...')  # 현재 크롤링 중인 페이지 출력
            
            # 페이지 번호를 URL에 반영하여 이동
            page_url = f"{url}?page={page}"  # URL에 페이지 번호 추가
            driver.get(page_url)
            time.sleep(2)  # 페이지 로딩 대기
            
            post_links = get_post_links(driver, page_url)
            for index, link in enumerate(post_links, start=(page - 1) * len(post_links) + 1):
                scrape_post(driver, link, index)  # 게시글 내용 크롤링 및 저장

            # 페이지네이션 오류나면 이 코드로 다시 해보기 (안될수도)
            if page < total_pages:
                try:
                    next_page_xpath = f"//a[@title='{page + 1}페이지']"
                    next_page_link = driver.find_element(By.XPATH, next_page_xpath)

                    if next_page_link.is_displayed() and next_page_link.is_enabled():
                        print(f'[DEBUG] 다음 페이지로 이동: {page + 1}')
                        next_page_link.click()
                        time.sleep(1)
                    else:
                        print("[DEBUG] 다음 페이지 버튼이 비활성화됨.")
                        break
                except Exception as e:
                    print(f"[DEBUG] {page}에서 {page+1}로 이동 실패: {e}")
                    break
            # 다음 페이지 이동
            # if page < total_pages:  # 마지막 페이지가 아닐 경우
            #     try:
            #         next_page_link = driver.find_element(By.XPATH, f"//a[@title='{page + 1}페이지']")
            #         next_page_link.click()
            #         time.sleep(1)  # 페이지 로딩 대기
            #     except Exception as e:
            #         print(f"페이지 {page}에서 {page + 1}로 이동 실패: {e}")
            #         break

    else:
        print(f"[INFO] 일반 텍스트 페이지 감지: {url}")
        scrape_text_page(driver, url,folder_path)


# 특정 페이지에서 게시글 링크 가져오기
def get_post_links(driver, url):
    driver.get(url)  # 해당 URL로 이동
    time.sleep(2)  # 페이지 로딩 대기
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')  # 페이지 소스 파싱
    table = soup.find('table', class_='board-table horizon1')  # 게시글이 있는 테이블 찾기
    links = []
    
    if table:
        rows = table.find('tbody').find_all('tr')  # 테이블 내의 모든 행(tr) 가져오기
        for row in rows:
            a_tag = row.find('a')  # <a> 태그 찾기
            if a_tag:
                post_url = "https://hansung.ac.kr" + a_tag['href']  # 전체 URL 생성
                links.append(post_url)  # 링크 리스트에 추가
    return links  # 게시글 링크 리스트 반환

def sanitize_filename(filename):
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return sanitized

# 게시글 내용 크롤링 및 파일 저장
def scrape_post(driver, post_url, index):
    driver.get(post_url)  # 해당 게시글 URL로 이동
    time.sleep(2)  # 페이지 로딩 대기
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')  # 페이지 소스 파싱
    title = soup.find(class_='view-title').text.strip()  # 제목 가져오기
    category = soup.find(class_='cate').find('dd').text.strip()  # 카테고리 가져오기
    date = soup.find(class_='write').find('dd').text.strip()  # 작성일 가져오기
    writer = soup.find(class_='writer').find('dd').text.strip()  # 작성자 가져오기
    views = soup.find(class_='count').find('dd').text.strip()  # 조회수 가져오기
    #content = soup.find(class_='view-con').text.strip()  # 본문 내용 가져오기
    
    #본문 내용 가져오기
    content_div = soup.find(class_='view-con')
    if content_div:
        paragraphs = content_div.find_all('p')  # 모든 <p> 태그 가져오기
        content_text = ""
        
        for paragraph in paragraphs:
            if paragraph.find_all('span'):
                # <span>이 있는 경우 span의 텍스트만 가져오기
                paragraph_text = "".join([span.get_text() for span in paragraph.find_all('span')])
            else:
                # <span>이 없으면 p 태그의 전체 텍스트 가져오기
                paragraph_text = paragraph.get_text()

            content_text += paragraph_text + "\n"  # 한 줄로 합쳐서 content_text에 추가
        
        content_text = content_text.strip()  # 마지막 불필요한 공백 제거
    else:
        content_text = "내용 없음"

    #본문 내 이미지 가져오기
    image_tags = content_div.find_all('img') if content_div else []
    image_urls = [img['src'] for img in image_tags if img.get('src')]
    
    #본문 내 테이블
    tables = content_div.find_all('table') if content_div else []
    markdown_tables = ""
    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue
        # 첫 번째 행을 헤더로 처리 (th가 없어도 td를 헤더로 간주)
        header_cells = [cell.get_text(strip=True) for cell in rows[0].find_all(['th', 'td'])]
        markdown_table = "| " + " | ".join(header_cells) + " |\n"
        markdown_table += "| " + " | ".join(["---"] * len(header_cells)) + " |\n"
        
        # 나머지 행들은 데이터로 처리
        for row in rows[1:]:
            data_cells = [cell.get_text(strip=True) for cell in row.find_all('td')]
            markdown_table += "| " + " | ".join(data_cells) + " |\n"
        
        markdown_tables += markdown_table + "\n\n"
    
    # 본문 내용에 테이블 포함시키기
    if markdown_tables:
        content_text += "\n\n" + markdown_tables

    # 저장할 폴더 생성
    folder_name = 'hsu_texts'
    os.makedirs(folder_name, exist_ok=True)  # 폴더가 없으면 생성

    try:
        sanitized_title = sanitize_filename(title) 
        file_name = os.path.join(folder_name, f'{sanitized_title}.txt')
        print(f"[DEBUG] 파일 저장 시도: {file_name}")

        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f'제목: {title}\n')
            f.write(f'카테고리: {category}\n')
            f.write(f'작성일: {date}\n')
            f.write(f'작성자: {writer}\n')
            f.write(f'조회수: {views}\n')
            f.write(f'내용:\n{content_text}\n')

    except Exception as e:
        print(f"[ERROR] 파일 저장 실패: {file_name} - 오류: {e}")

    # 첨부파일 다운로드
    file_section = soup.find(class_='view-file')  # 첨부파일 섹션 찾기
    if file_section:
        file_links = file_section.find_all('a')  # 모든 파일 링크 가져오기
        for file_link in file_links:
            file_url = "https://hansung.ac.kr" + file_link['href']  # 파일 다운로드 URL
            file_name = file_link.text.strip()  # 파일 이름
            download_file(file_url, title, file_name, folder_name)  # 파일 다운로드 함수 호출

    driver.back()  # 원래 페이지(게시글 목록)로 돌아가기
    time.sleep(2)  # 페이지 로딩 대기

def sanitize_filename(filename):
    """파일명에서 사용할 수 없는 문자 제거"""
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
    return sanitized

def download_file(url, title, file_name, folder_name):
    """파일 다운로드 함수"""
    try:
        # 파일명을 {title}_원래파일이름 형식으로 수정
        sanitized_title = sanitize_filename(title)
        sanitized_file_name = sanitize_filename(file_name)

        base_name, file_extension = os.path.splitext(sanitized_file_name)  # 확장자 추출
        new_file_name = f"{sanitized_title}_{base_name}{file_extension}"  # 제목 + 파일명 + 확장자

        # 동일한 파일이 존재할 경우 번호 추가
        count = 1
        file_path = os.path.join(folder_name, new_file_name)
        while os.path.exists(file_path):  # 동일한 이름의 파일이 존재하면
            new_file_name = f"{sanitized_title}_{base_name}_{count}{file_extension}"  # 번호 추가
            file_path = os.path.join(folder_name, new_file_name)
            count += 1

        # 파일 다운로드
        response = requests.get(url, stream=True)  # 파일 요청
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(1024):  # 파일을 1024바이트씩 저장
                    f.write(chunk)
            print(f'Downloaded: {file_path}')  # 다운로드 완료 메시지 출력
        else:
            print(f'Failed to download: {file_name}')  # 다운로드 실패 메시지 출력
    except Exception as e:
        print(f"[ERROR] 파일 다운로드 실패: {file_name} - 오류: {e}")

def scrape_text_page(driver, url,folder_path):
    driver.get(url)
    time.sleep(2)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    title_element = soup.find(class_="page_title")
    contents_element = soup.find(class_="contents")

    title = title_element.get_text(strip=True) if title_element else "제목 없음"
    content = ""
    if contents_element:
        # 불필요한 요소 제거
        for contnt_master in contents_element.find_all(class_="contntMaster"):
            contnt_master.decompose()
        for contnt_master in contents_element.find_all(class_="_paging"):
            contnt_master.decompose()
        
        # <article id="_contentBuilder"> 내용 가져오기
        article_element = contents_element.find("article", id="_contentBuilder")
        content = article_element.get_text(separator='\n', strip=True) if article_element else "내용 없음"

    # URL을 파일명으로 변환 (파일명에 사용할 수 없는 문자 제거)
    file_name = url.replace('https://', '').replace('http://', '').replace('/', '_') + '.txt'
    folder_name = folder_path
    os.makedirs(folder_name, exist_ok=True)
    file_path = os.path.join(folder_name, file_name)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(title + "\n\n" + content)
    
    print(f"[INFO] 저장 완료: {file_path}")

def scrape_all_links(folder_path, base_url):
    driver = setup_driver()
    all_links = get_main_links(driver, base_url)
    
    for link in all_links:
        scrape_all_pages(driver, link, folder_path)
    
    driver.quit()

def get_main_links(driver, base_url):
    driver.get(base_url)
    time.sleep(2)  # 페이지 로딩 대기
    
    main_links = []
    
    # "top_div div_1" 내의 ul > li > a 태그 찾기
    top_div = driver.find_element(By.CLASS_NAME, "top_div.div_1")
    main_menu_items = top_div.find_elements(By.TAG_NAME, "a")
    
    for item in main_menu_items:
        href = item.get_attribute("href")  # <a> 태그의 href 가져오기
        # 특정 URL을 제외
        if href == "https://www.hansung.ac.kr/hansung/8385/subview.do":
            print(f"[INFO] 제외된 링크: {href}")
            continue  # 해당 링크는 크롤링하지 않고 넘어가기
        
        main_links.append(href)  # 링크 리스트에 추가
    
    return main_links  # 모든 메인 메뉴 링크 반환


if __name__ == '__main__':
    folder_path = "./hsu_texts"
    base_url = "https://hansung.ac.kr/sites/CSE/index.do"
    #scrape_all_links(folder_path, base_url)
    convert2txt(folder_path)

