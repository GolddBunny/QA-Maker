import os
from pathlib import Path

def main(output_dir, page_id):
    """텍스트 파일의 줄바꿈을 제거하는 메인 함수"""
    try:
        output_path = Path(output_dir)
        
        if not output_path.exists():
            return {
                "success": False,
                "error": f"지정된 경로를 찾을 수 없습니다: {output_dir}"
            }
        
        total_processed_files = 0
        processed_folders = {}
        
        # output_dir 내의 모든 하위 폴더를 재귀적으로 탐색
        for root, dirs, files in os.walk(output_path):
            folder_processed_files = 0
            relative_folder = os.path.relpath(root, output_path)
            
            # txt 파일들을 찾아서 처리
            for filename in files:
                if filename.endswith(".txt"):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        # 줄바꿈 문자 제거
                        one_line_content = content.replace('\n', '').replace('\r', '')
                        # 같은 파일에 덮어쓰기
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(one_line_content)
                        folder_processed_files += 1
                        total_processed_files += 1
                    except Exception as file_error:
                        print(f"⚠️ 파일 처리 실패: {file_path} - {file_error}")
            
            # 처리된 파일이 있는 폴더만 기록
            if folder_processed_files > 0:
                if relative_folder == ".":
                    folder_display = "루트 폴더"
                else:
                    folder_display = relative_folder
                processed_folders[folder_display] = folder_processed_files
                print(f"📁 {folder_display}에서 {folder_processed_files}개 파일 처리 완료")
        
        if total_processed_files == 0:
            return {
                "success": False,
                "error": f"처리할 txt 파일을 찾을 수 없습니다. 경로: {output_dir}"
            }
        
        # 처리된 폴더 정보를 문자열로 변환
        folder_summary = [f"{folder}: {count}개" for folder, count in processed_folders.items()]
        
        return {
            "success": True,
            "processed_files": total_processed_files,
            "processed_folders": processed_folders,
            "message": f"총 {total_processed_files}개 파일 처리 완료 ({', '.join(folder_summary)})"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"텍스트 정리 중 오류: {str(e)}"
        }

if __name__ == "__main__":
    # 테스트용 실행
    import sys
    if len(sys.argv) >= 3:
        result = main(sys.argv[1], sys.argv[2])
    else:
        result = main("./test_output", "test_page")
    
    if result["success"]:
        print(result["message"])
    else:
        print(f"오류: {result['error']}")