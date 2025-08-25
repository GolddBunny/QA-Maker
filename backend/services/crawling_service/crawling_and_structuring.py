#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 크롤링 시스템 테스트 스크립트
html_Structuring.py를 사용하여 Jina와 artclView 크롤러를 통합 실행
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from services.crawling_service.html_Structuring import crawl_from_file

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
        print(f"통합 크롤링 시스템 시작 - Page ID: {page_id}")
        
        if not url_list:
            return {
                "success": False,
                "error": "크롤링할 URL이 없습니다."
            }
        
        # URL 리스트에서 URL만 추출
        urls = [item['url'] for item in url_list if 'url' in item]
        
        if not urls:
            print(f"crawling_and_structuring.py: 유효한 URL이 없습니다.")
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
        
        print(f"임시 URL 파일: {temp_url_file}")
        print(f"저장 경로: {url_input_path}")
        print(f"크롤링할 URL 개수: {len(urls)}")
        
        try:
            # 통합 크롤링 실행
            results = crawl_from_file(
                url_file_path=temp_url_file,
                page_id=page_id,
                output_base_dir=str(url_input_path),
                verbose=True
            )
            
            # 임시 파일 삭제
            os.unlink(temp_url_file)
            
            # 결과 처리
            if "error" not in results:
                print("통합 크롤링 성공!")
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
            # 임시 파일 삭제
            if os.path.exists(temp_url_file):
                os.unlink(temp_url_file)
            raise e
            
    except Exception as e:
        print(f"예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": f"크롤링 중 예외 발생: {str(e)}"
        }

# def test_integrated_crawling():
#     """통합 크롤링 테스트 함수"""
#     print("통합 크롤링 시스템 테스트 시작")
    
#     # 테스트용 URL 파일 경로
#     url_file_path = Path(__file__).parent.parent.parent / "data/crawling/20250526_0412_hansung_ac_kr_sites_hansung/page_urls_20250526_0412.txt"
    
#     # 사용자 지정 저장 경로
#     custom_output_dir = Path(__file__).parent.parent.parent / "data" / "crawling" / "20250526_0412_hansung_ac_kr_sites_hansung"
    
#     if not url_file_path.exists():
#         print(f"URL 파일을 찾을 수 없습니다: {url_file_path}")
#         return
    
#     print(f"URL 파일: {url_file_path}")
#     print(f"저장 경로: {custom_output_dir}")
    
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
#             print("\n통합 크롤링 성공!")
#             print(f"총 성공한 파일: {results.get('total_success_count', 0)}개")
#             print(f"저장 위치: {results.get('output_base_dir', 'N/A')}")
            
#             # artclView 결과
#             artcl_results = results.get('artcl_results', {})
#             if artcl_results:
#                 print(f"artclView 크롤링: {artcl_results.get('success_count', 0)}개 파일")
#                 print(f"첨부파일: {artcl_results.get('attachment_count', 0)}개")
#                 print(f"저장 경로: {artcl_results.get('output_dir', 'N/A')}")
            
#             # Jina 결과
#             jina_results = results.get('jina_results', {})
#             if jina_results:
#                 print(f"Jina 크롤링: {jina_results.get('success_count', 0)}개 파일")
#                 print(f"저장 경로: {jina_results.get('output_dir', 'N/A')}")
            
#             # 오류 정보
#             errors = results.get('errors', [])
#             if errors:
#                 print(f"발생한 오류: {len(errors)}개")
#                 for error in errors:
#                     print(f"   - {error}")
            
#             print(f"실행 시간: {results.get('execution_time', 'N/A')}")
            
#         else:
#             print(f"크롤링 실패: {results.get('error', '알 수 없는 오류')}")
            
#     except Exception as e:
#         print(f"예외 발생: {e}")
#         import traceback
#         traceback.print_exc()

# if __name__ == "__main__":
#     test_integrated_crawling() 