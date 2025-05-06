import requests
import os
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime

def jina_crawling(crawl_url):
    url = f"https://r.jina.ai/{crawl_url}"
    headers = {"X-Md-Heading-Style": "setext", "X-Remove-Selector": "header, .class, #id, a href, href, popup"}
    response = requests.get(url, headers=headers)
    
    parsed_url = urlparse(url)
    
    # Title 추출 시도
    title = None
    try:
        # response.text에서 Title: 다음에 오는 텍스트 추출
        title_match = re.search(r'Title:\s*(.*?)(?:\n|$)', response.text)
        if title_match:
            title = title_match.group(1).strip()
            # 파일명으로 사용할 수 있도록 특수문자 제거 및 길이 제한
            title = re.sub(r'[\\/*?:"<>|]', '', title)  # 파일명에 사용할 수 없는 문자 제거
            if len(title) > 50:  # 제목이 너무 길면 자르기
                title = title[:50]
    except:
        title = None
        
    # BASE_DIR 정의
    BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "crawling", "jina_crawling")
    
    # 오늘 날짜와 시간으로 파일명 생성
    date_time_str = datetime.now().strftime('%y%m%d_%H%M')
    
    # 파일명 생성 (도메인 제외하고 제목 추가)
    if title:
        filename = f"{date_time_str}_{title}.txt"
    else:
        # 원본 URL에서 페이지 이름 추출 시도
        try:
            page_name = crawl_url.split('/')[-1].split('.')[0]
            if page_name:
                filename = f"{date_time_str}_{page_name}.txt"
            else:
                filename = f"{date_time_str}.txt"
        except:
            filename = f"{date_time_str}.txt"
    
    # 폴더 생성 (BASE_DIR만 있는지 확인)
    os.makedirs(BASE_DIR, exist_ok=True)
    
    # 파일 경로
    file_path = os.path.join(BASE_DIR, filename)
    
    print(f"크롤링 결과 저장 경로: {file_path}")
    
    # 응답 내용 파일로 저장
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    return file_path

if __name__ == "__main__":
    jina_crawling("https://hansung.ac.kr/hansung/8385/subview.do?enc=Zm5jdDF8QEB8JTJGYmJzJTJGaGFuc3VuZyUyRjE0MyUyRjI2ODM5MiUyRmFydGNsVmlldy5kbyUzRnBhZ2UlM0QxJTI2c3JjaENvbHVtbiUzRCUyNnNyY2hXcmQlM0QlMjZiYnNDbFNlcSUzRCUyNmJic09wZW5XcmRTZXElM0QlMjZyZ3NCZ25kZVN0ciUzRCUyNnJnc0VuZGRlU3RyJTNEJTI2aXNWaWV3TWluZSUzRGZhbHNlJTI2cGFzc3dvcmQlM0QlMjY%3D")
