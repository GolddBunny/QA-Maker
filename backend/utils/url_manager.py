import os
import json
import datetime

class URLManager:
    def __init__(self):
        # data/urls.json 경로 설정
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.file_path = os.path.join(base_dir, "data", "urls", "urls.json")
        
        # 디렉토리 존재 확인 및 생성
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        # 파일이 존재하지 않으면 빈 딕셔너리로 초기화
        if not os.path.exists(self.file_path):
            self.save_all_urls({})
    
    def save_all_urls(self, urls_dict):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(urls_dict, f, ensure_ascii=False, indent=4)
    
    def load_all_urls(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def load_urls(self, page_id):
        urls_dict = self.load_all_urls()
        urls = urls_dict.get(page_id, [])
        
        # 기존 문자열 URL을 객체 형태로 변환 (이전 데이터 호환성 유지)
        updated_urls = []
        for item in urls:
            if isinstance(item, str):
                # 기본 날짜로 '-'를 사용하여 이전 데이터 표시
                updated_urls.append({'url': item, 'date': '-'})
            else:
                updated_urls.append(item)
        
        return updated_urls
    
    def save_urls(self, page_id, urls):
        # 전체 URL 딕셔너리를 로드하고 업데이트
        urls_dict = self.load_all_urls()
        urls_dict[page_id] = urls
        # 업데이트된 딕셔너리를 저장
        self.save_all_urls(urls_dict)
    
    def add_url(self, page_id, new_url):
        urls = self.load_urls(page_id)
        # 현재 날짜 생성 (YYYY-MM-DD 형식)
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        existing_urls = [item['url'] for item in urls]
        if new_url not in existing_urls:
            # URL과 날짜를 객체로 저장
            url_object = {
                'url': new_url,
                'date': current_date
            }
            urls.append(url_object)
            self.save_urls(page_id, urls)
        
        return urls
    
    def add_urls(self, page_id, new_urls):
        urls = self.load_urls(page_id)
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 기존 URL 목록에서 URL만 추출
        existing_urls = [item['url'] for item in urls]
        
        # 새로운 URL 추가 (중복 제거)
        for url in new_urls:
            if url not in existing_urls:
                urls.append({
                    'url': url,
                    'date': current_date
                })
                existing_urls.append(url)  # 추가된 URL 등록
        
        self.save_urls(page_id, urls)
        return urls
    
    def get_all_page_ids(self):
        return list(self.load_all_urls().keys())