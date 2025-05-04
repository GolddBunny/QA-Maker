import os
import json

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
        return urls_dict.get(page_id, [])
    
    def save_urls(self, page_id, urls):
        # 중복 제거
        unique_urls = list(set(urls))
        
        # 전체 URL 딕셔너리를 로드하고 업데이트
        urls_dict = self.load_all_urls()
        urls_dict[page_id] = unique_urls
        
        # 업데이트된 딕셔너리를 저장
        self.save_all_urls(urls_dict)
    
    def add_url(self, page_id, new_url):
        urls = self.load_urls(page_id)
        
        # URL이 이미 목록에 있는지 확인
        if new_url not in urls:
            urls.append(new_url)
            self.save_urls(page_id, urls)
        
        return urls
    
    def add_urls(self, page_id, new_urls):
        urls = self.load_urls(page_id)
        updated_urls = list(set(urls + new_urls))  # 중복 제거
        self.save_urls(page_id, updated_urls)
        return updated_urls
    
    def get_all_page_ids(self):
        return list(self.load_all_urls().keys())