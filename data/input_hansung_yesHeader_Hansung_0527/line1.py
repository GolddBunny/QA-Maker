import os
from pathlib import Path

# 현재 파일이 위치한 폴더(즉, txt 파일들이 있는 폴더)
folder_path = Path(__file__).parent / "input" / "jina_crawling"

# 폴더 내 모든 파일 확인
for filename in os.listdir(folder_path):
    if filename.endswith(".txt"):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 줄바꿈 문자 제거
        one_line_content = content.replace('\n', '').replace('\r', '')
        # 같은 파일에 덮어쓰기
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(one_line_content)