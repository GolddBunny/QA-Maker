import base64
import urllib.parse

def transform_hansung_url(original_url):
    """
    한성대학교 원본 URL을 인코딩된 URL로 변환하는 함수
    
    Args:
        original_url (str): 원본 URL (예: https://hansung.ac.kr/bbs/CSE/1248/268311/artclView.do)
        
    Returns:
        str: 변환된 URL
    """
    # 1. 원본 URL에서 도메인을 제외한 경로 부분 추출
    path = original_url.replace("https://hansung.ac.kr", "")
    
    # 2. 기본 쿼리 파라미터 추가
    full_path = path + "?page=1&srchColumn=&srchWrd=&bbsClSeq=&bbsOpenWrdSeq=&rgsBgndeStr=&rgsEnddeStr=&isViewMine=false&password=&"
    
    # 3. URL 인코딩
    url_encoded = urllib.parse.quote(full_path)
    
    # 4. 접두어 추가
    prefixed = "fnct1|@@|" + url_encoded
    
    # 5. Base64 인코딩
    base64_encoded = base64.b64encode(prefixed.encode('utf-8')).decode('utf-8')
    
    # 6. 최종 URL 생성
    transformed_url = f"https://hansung.ac.kr/CSE/10766/subview.do?enc={base64_encoded}"
    
    return transformed_url

# 사용 예시
if __name__ == "__main__":
    # 단일 URL 변환
    original_url = "https://hansung.ac.kr/bbs/CSE/1248/268311/artclView.do"
    transformed_url = transform_hansung_url(original_url)
    print(f"원본 URL: {original_url}")
    print(f"변환된 URL: {transformed_url}")
    
    # 여러 URL 일괄 변환 예시
    urls = [
        "https://hansung.ac.kr/bbs/CSE/1248/268311/artclView.do",
        "https://hansung.ac.kr/bbs/CSE/1248/268312/artclView.do",
        "https://hansung.ac.kr/bbs/CSE/1248/268313/artclView.do",
        "https://hansung.ac.kr/curriculum/CSE/144/887/artclView.do",
    ]
    
    transformed_urls = [transform_hansung_url(url) for url in urls]
    
    print("\n여러 URL 일괄 변환 결과:")
    for i, (original, transformed) in enumerate(zip(urls, transformed_urls)):
        print(f"{i+1}. 원본: {original}")
        print(f"   변환: {transformed}")
        print()