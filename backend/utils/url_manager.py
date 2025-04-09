import os
import json

class URLManager:
    def __init__(self, file_path='data/urls.json'):
        self.file_path = file_path
        # 디렉토리 존재 확인 및 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    def save_urls(self, urls):
        # 주어진 URL 리스트를 저장 urls (list): 저장할 URL 목록
        # 중복 제거
        unique_urls = list(set(urls))
        
        # JSON 파일로 저장
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(unique_urls, f, ensure_ascii=False, indent=4)
    
    def load_urls(self):
        # 저장된 URL 리스트 로드 list: 저장된 URL 목록
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def add_urls(self, new_urls):
        # 새로운 URL들을 기존 목록에 추가 new_urls (list): 추가할 URL 목록
        existing_urls = self.load_urls()
        updated_urls = list(set(existing_urls + new_urls)) # 중복 제거
        self.save_urls(updated_urls)
        return updated_urls 