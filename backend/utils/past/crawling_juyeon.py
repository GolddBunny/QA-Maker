"""
input: 한성대학교의 특정 페이지
- 웹페이지의 텍스트, 표, 이미지 추출
- KeyBERT: 텍스트에서 키워드 추출
- OCR(pytesseract): 이미지에서 텍스트 추출
output: 'hsu_crawling.txt'
"""

import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from keybert import KeyBERT
from PIL import Image
from io import BytesIO
import pytesseract

# KeyBERT 초기화
kw_model = KeyBERT()

# 크롬 드라이버 설정
options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
service = Service()
driver = webdriver.Chrome(service=service, options=options)

# 크롤링할 웹사이트 목록
urls = [
    'https://www.hansung.ac.kr/hansung/3871/subview.do',
]

# 저장 경로
file_path = "/Users/jy/Documents/qa_system/HSU_CRAWLING/hsu_crawling.txt"

# 기존 파일 삭제 후 새로 저장
if os.path.exists(file_path):
    os.remove(file_path)

# 모든 데이터를 저장할 리스트
all_data = []

def extract_clean_text(soup):
    # HTML에서 주요 텍스트 추출
    important_texts = []
    
    for tag in soup.find_all(["h1", "h2", "h3"]):
        important_texts.append(f"{tag.get_text(strip=True)}")

    for tag in soup.find_all(["div"]):
        text = tag.get_text(strip=True)
        if text:
            important_texts.append(text)

    return "\n".join(important_texts)

def extract_tables(soup):
    # HTML에서 표(테이블) 데이터 추출
    tables = []
    
    for table in soup.find_all("table"):
        table_data = []
        for row in table.find_all("tr"):
            columns = [col.get_text(strip=True) for col in row.find_all(["td", "th"])]
            table_data.append(columns)
        if table_data:
            tables.append(table_data)

    return tables

def extract_images(soup, base_url):
    # HTML에서 이미지 URL 추출
    images = []
    for img in soup.find_all("img"):
        img_url = img.get("src")
        if img_url:
            if not img_url.startswith("http"):  
                img_url = base_url + img_url
            images.append(img_url)
    return images

def extract_text_from_image(image_url):
    # OCR을 이용해 이미지 속 텍스트 추출
    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code != 200 or not response.content:
            return f"이미지 다운로드 실패: {image_url}"
        
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            return f"잘못된 이미지 유형: {content_type} ({image_url})"

        img = Image.open(BytesIO(response.content))
        text = pytesseract.image_to_string(img, lang="kor+eng")
        return text.strip()
    except (requests.RequestException, Image.UnidentifiedImageError) as e:
        return f"이미지 처리 실패: {image_url} - {e}"

# 모든 URL을 순회하며 크롤링
for url in urls:
    print(f"크롤링 중: {url}")
    driver.get(url)
    time.sleep(3)

    # 페이지 소스 파싱
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # 텍스트, 표, 이미지 크롤링
    extracted_text = extract_clean_text(soup)
    tables = extract_tables(soup)
    images = extract_images(soup, url)

    # 이미지 속 텍스트 추출 (OCR 적용)
    image_texts = [extract_text_from_image(img) for img in images]

    # KeyBERT 키워드 및 문장 추출
    keywords = kw_model.extract_keywords(extracted_text, keyphrase_ngram_range=(1, 2), stop_words=None, top_n=10)
    keyword_list = [kw[0] for kw in keywords]

    # 크롤링된 데이터를 저장
    page_data = [
        f"사이트: {url}",
        f"키워드: {', '.join(keyword_list)}",
        f"전체 텍스트:\n{extracted_text}",
        f"표 데이터: {tables}",
        f"이미지 URL: {images}",
        f"OCR로 추출된 이미지 속 텍스트:\n{image_texts}",
    ]
    
    all_data.append("\n".join(page_data))
    print(f"✅ {url} 크롤링 완료!")

# 모든 데이터를 파일로 저장
with open(file_path, "w", encoding="utf-8") as file:
    file.write("\n\n".join(all_data))

print(f"\n모든 데이터를 '{file_path}'에 저장 완료!")