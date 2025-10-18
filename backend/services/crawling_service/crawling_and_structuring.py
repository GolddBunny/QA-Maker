# url list를 받아서 크롤링 시작 -> html_Structuring.py 호출 ( -> Jina, artclView 크롤링 시작 - > 크롤링 결과 저장) -> 크롤링 결과 반환

import os
import tempfile
import json
from pathlib import Path
from services.crawling_service.html_Structuring import crawl_from_file

def extract_url_breadcrumb_mapping(page_id):
    """URL 트리 JSON 파일에서 URL-breadcrumb 매핑을 추출"""
    try:
        # URL 트리 JSON 파일 경로 찾기 (여러 경로 시도)
        possible_paths = [
            Path("../data/crawling"),
            Path(__file__).parent / "urlCrawling_CSE"
        ]
        
        crawling_dir = None
        for path in possible_paths:
            print(f"🔍 크롤링 디렉토리 확인: {path.absolute()}")
            if path.exists():
                crawling_dir = path
                print(f"✅ 크롤링 디렉토리 발견: {crawling_dir}")
                break
        
        if crawling_dir is None:
            print("❌ 크롤링 디렉토리를 찾을 수 없습니다.")
            return {}
        
        # page_id와 관련된 디렉토리 찾기 (범용적 매칭)
        found_dirs = []
        matching_dirs = []
        
        for dir_path in crawling_dir.iterdir():
            if dir_path.is_dir():
                found_dirs.append(dir_path.name)
                # page_id가 디렉토리명에 포함되어 있는지 확인 (대소문자 무시)
                if (page_id in dir_path.name or 
                    page_id.lower() in dir_path.name.lower()):
                    matching_dirs.append(dir_path)
        
        # 매칭된 디렉토리가 없으면 가장 최근 디렉토리 사용
        if not matching_dirs:
            print(f"⚠️ page_id '{page_id}'와 정확히 매칭되는 디렉토리를 찾을 수 없습니다.")
            print(f"📁 발견된 디렉토리들: {found_dirs}")
            # 가장 최근 디렉토리 선택 (타임스탬프 기준)
            timestamp_dirs = [d for d in crawling_dir.iterdir() if d.is_dir() and any(c.isdigit() for c in d.name[:8])]
            if timestamp_dirs:
                matching_dirs = [sorted(timestamp_dirs, key=lambda x: x.name, reverse=True)[0]]
                print(f"🕒 가장 최근 디렉토리 사용: {matching_dirs[0].name}")
        
        # 매칭된 디렉토리들에서 JSON 파일 찾기
        for dir_path in matching_dirs:
            print(f"✅ 매칭 디렉토리 발견: {dir_path}")
            
            # url_tree_*.json 파일 찾기
            json_files = list(dir_path.glob("url_tree_*.json"))
            print(f"📄 JSON 파일 개수: {len(json_files)}")
            
            for json_file in json_files:
                print(f"📖 JSON 파일 읽기: {json_file}")
                with open(json_file, 'r', encoding='utf-8') as f:
                    tree_data = json.load(f)
                
                # 재귀적으로 URL-breadcrumb 매핑 추출
                url_breadcrumb_map = {}
                
                def extract_from_node(node):
                    if 'url' in node and 'breadcrumb' in node:
                        url_breadcrumb_map[node['url']] = node['breadcrumb']
                    
                    if 'children' in node:
                        for child in node['children']:
                            extract_from_node(child)
                
                extract_from_node(tree_data)
                print(f"✅ 매핑 추출 완료: {len(url_breadcrumb_map)}개")
                
                # 디버깅: 추출된 매핑의 샘플 출력
                if url_breadcrumb_map:
                    print("📋 추출된 매핑 샘플:")
                    for i, (url, breadcrumb) in enumerate(list(url_breadcrumb_map.items())[:3]):
                        print(f"   {i+1}. {url} -> {breadcrumb}")
                
                return url_breadcrumb_map
        
        print("❌ 유효한 JSON 파일을 찾을 수 없습니다.")
        return {}
    except Exception as e:
        print(f"Breadcrumb 매핑 추출 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def main(page_id, url_list):
    """
    메인 크롤링 함수
    Args:
        page_id (str): 페이지 ID
        url_list (list): URL 딕셔너리 리스트 [{'url': 'http://...', 'date': '2025-01-01'}, ...]
    Returns:
        dict: 크롤링 결과
    """
    try:
        print(f"🚀 통합 크롤링 시스템 시작 - Page ID: {page_id}")
        
        if not url_list:
            return {
                "success": False,
                "error": "크롤링할 URL이 없습니다."
            }
        
        # URL 리스트에서 URL만 추출
        urls = [item['url'] for item in url_list if 'url' in item]
        
        if not urls:
            print("crawling_and_structuring.py: 🔄 유효한 URL이 없습니다.")
            return {
                "success": False,
                "error": "유효한 URL이 없습니다."
            }
        
        # 임시 URL 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
            for url in urls:
                temp_file.write(f"{url}\n")
            temp_url_file = temp_file.name
        
        # 출력 디렉토리 설정 - document_routes.py와 동일한 방식 사용
        # Flask가 backend에서 실행되므로 ../data/input/ 사용
        url_base_path = Path(f"../data/input/{page_id}_url")
        url_input_path = url_base_path / "input"
        
        # 디렉토리 생성
        url_input_path.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 임시 URL 파일: {temp_url_file}")
        print(f"💾 저장 경로: {url_input_path}")
        print(f"🔗 크롤링할 URL 개수: {len(urls)}")
        
        try:
            # URL-breadcrumb 매핑 추출
            url_breadcrumb_map = extract_url_breadcrumb_mapping(page_id)
            print(f"📍 Breadcrumb 매핑 추출: {len(url_breadcrumb_map)}개 URL")
            
            # 디버깅: 매핑 내용 일부 출력
            if url_breadcrumb_map:
                print("📋 Breadcrumb 매핑 샘플:")
                for i, (url, breadcrumb) in enumerate(list(url_breadcrumb_map.items())[:3]):
                    print(f"   {i+1}. {url} -> {breadcrumb}")
            else:
                print("⚠️ Breadcrumb 매핑이 비어있습니다!")
            
            # 통합 크롤링 실행
            results = crawl_from_file(
                url_file_path=temp_url_file,
                page_id=page_id,
                output_base_dir=str(url_input_path),
                url_breadcrumb_map=url_breadcrumb_map,
                verbose=True
            )
            
            # 임시 파일 삭제
            os.unlink(temp_url_file)
            
            # 결과 처리
            if "error" not in results:
                print("✅ 통합 크롤링 성공!")
                return {
                    "success": True,
                    "results": {
                        "page_id": page_id,
                        "total_success_count": results.get('total_success_count', 0),
                        "output_dir": str(url_input_path),
                        "artcl_results": results.get('artcl_results', {}),
                        "jina_results": results.get('jina_results', {}),
                        "execution_time": results.get('execution_time', 'N/A'),
                        "errors": results.get('errors', [])
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"크롤링 실패: {results.get('error', '알 수 없는 오류')}"
                }
                
        except Exception as e:
            # 임시 파일 삭제 (오류 발생 시에도)
            if os.path.exists(temp_url_file):
                os.unlink(temp_url_file)
            raise e
            
    except Exception as e:
        print(f"💥 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"크롤링 중 예외 발생: {str(e)}"
        }

# def test_integrated_crawling():
#     """통합 크롤링 테스트 함수"""
#     print("🚀 통합 크롤링 시스템 테스트 시작")
    
#     # 테스트용 URL 파일 경로
#     url_file_path = Path(__file__).parent.parent.parent / "data/crawling/20250526_0412_hansung_ac_kr_sites_hansung/page_urls_20250526_0412.txt"
    
#     # 사용자 지정 저장 경로
#     custom_output_dir = Path(__file__).parent.parent.parent / "data" / "crawling" / "20250526_0412_hansung_ac_kr_sites_hansung"
    
#     if not url_file_path.exists():
#         print(f"❌ URL 파일을 찾을 수 없습니다: {url_file_path}")
#         return
    
#     print(f"📁 URL 파일: {url_file_path}")
#     print(f"💾 저장 경로: {custom_output_dir}")
    
#     try:
#         # 통합 크롤링 실행
#         results = crawl_from_file(
#             str(url_file_path),
#             output_base_dir=str(custom_output_dir),
#             max_workers=3,
#             delay_range=(1.0, 2.0),
#             verbose=True
#         )
        
#         # 결과 출력
#         if "error" not in results:
#             print("\n✅ 통합 크롤링 성공!")
#             print(f"📊 총 성공한 파일: {results.get('total_success_count', 0)}개")
#             print(f"📁 저장 위치: {results.get('output_base_dir', 'N/A')}")
            
#             # artclView 결과
#             artcl_results = results.get('artcl_results', {})
#             if artcl_results:
#                 print(f"🔗 artclView 크롤링: {artcl_results.get('success_count', 0)}개 파일")
#                 print(f"   📎 첨부파일: {artcl_results.get('attachment_count', 0)}개")
#                 print(f"   📂 저장 경로: {artcl_results.get('output_dir', 'N/A')}")
            
#             # Jina 결과
#             jina_results = results.get('jina_results', {})
#             if jina_results:
#                 print(f"🤖 Jina 크롤링: {jina_results.get('success_count', 0)}개 파일")
#                 print(f"   📂 저장 경로: {jina_results.get('output_dir', 'N/A')}")
            
#             # 오류 정보
#             errors = results.get('errors', [])
#             if errors:
#                 print(f"⚠️  발생한 오류: {len(errors)}개")
#                 for error in errors:
#                     print(f"   - {error}")
            
#             print(f"⏱️  실행 시간: {results.get('execution_time', 'N/A')}")
            
#         else:
#             print(f"❌ 크롤링 실패: {results.get('error', '알 수 없는 오류')}")
            
#     except Exception as e:
#         print(f"💥 예외 발생: {e}")
#         import traceback
#         traceback.print_exc()

def test_breadcrumb_extraction(page_id):
    """Breadcrumb 매핑 추출 테스트
    
    Args:
        page_id (str): 테스트할 페이지 ID
    """
    print(f"🧪 Breadcrumb 매핑 추출 테스트 시작 - Page ID: {page_id}")
    mapping = extract_url_breadcrumb_mapping(page_id)
    print(f"📊 테스트 결과: {len(mapping)}개 매핑 추출")
    if mapping:
        print("📋 추출된 매핑:")
        for i, (url, breadcrumb) in enumerate(list(mapping.items())[:5]):
            print(f"  {i+1}. {url}")
            print(f"      -> {breadcrumb}")
    else:
        print("❌ 매핑이 추출되지 않았습니다.")
    return mapping

def test_crawling_with_breadcrumb(page_id, test_urls):
    """실제 크롤링에서 breadcrumb이 포함되는지 테스트
    
    Args:
        page_id (str): 페이지 ID
        test_urls (list): 테스트용 URL 리스트
    """
    print(f"\n🧪 통합 크롤링 breadcrumb 테스트 시작 - Page ID: {page_id}")
    
    try:
        result = main(page_id, test_urls)
        print(f"📊 크롤링 테스트 결과: {result}")
        return result
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

# if __name__ == "__main__":
#     # 개별 테스트 실행 예시
#     # test_page_id = "your_page_id_here"
#     # test_urls = [{"url": "your_test_url_here"}]
#     # test_breadcrumb_extraction(test_page_id)
#     # test_crawling_with_breadcrumb(test_page_id, test_urls) 