#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 크롤링 시스템 테스트 스크립트
html_Structuring.py를 사용하여 Jina와 artclView 크롤러를 통합 실행
"""

import os
import sys
from pathlib import Path

# 현재 파일의 디렉토리를 기준으로 backend 디렉토리를 sys.path에 추가
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

from utils.html_Structuring import crawl_from_file

def test_integrated_crawling():
    """통합 크롤링 테스트 함수"""
    print("🚀 통합 크롤링 시스템 테스트 시작")
    
    # 테스트용 URL 파일 경로
    url_file_path = Path(__file__).parent.parent.parent / "data/crawling/20250526_0412_hansung_ac_kr_sites_hansung/page_urls_20250526_0412.txt"
    
    # 사용자 지정 저장 경로
    custom_output_dir = Path(__file__).parent.parent.parent / "data" / "crawling" / "20250526_0412_hansung_ac_kr_sites_hansung"
    
    if not url_file_path.exists():
        print(f"❌ URL 파일을 찾을 수 없습니다: {url_file_path}")
        return
    
    print(f"📁 URL 파일: {url_file_path}")
    print(f"💾 저장 경로: {custom_output_dir}")
    
    try:
        # 통합 크롤링 실행
        results = crawl_from_file(
            str(url_file_path),
            output_base_dir=str(custom_output_dir),
            max_workers=3,
            delay_range=(1.0, 2.0),
            verbose=True
        )
        
        # 결과 출력
        if "error" not in results:
            print("\n✅ 통합 크롤링 성공!")
            print(f"📊 총 성공한 파일: {results.get('total_success_count', 0)}개")
            print(f"📁 저장 위치: {results.get('output_base_dir', 'N/A')}")
            
            # artclView 결과
            artcl_results = results.get('artcl_results', {})
            if artcl_results:
                print(f"🔗 artclView 크롤링: {artcl_results.get('success_count', 0)}개 파일")
                print(f"   📎 첨부파일: {artcl_results.get('attachment_count', 0)}개")
                print(f"   📂 저장 경로: {artcl_results.get('output_dir', 'N/A')}")
            
            # Jina 결과
            jina_results = results.get('jina_results', {})
            if jina_results:
                print(f"🤖 Jina 크롤링: {jina_results.get('success_count', 0)}개 파일")
                print(f"   📂 저장 경로: {jina_results.get('output_dir', 'N/A')}")
            
            # 오류 정보
            errors = results.get('errors', [])
            if errors:
                print(f"⚠️  발생한 오류: {len(errors)}개")
                for error in errors:
                    print(f"   - {error}")
            
            print(f"⏱️  실행 시간: {results.get('execution_time', 'N/A')}")
            
        else:
            print(f"❌ 크롤링 실패: {results.get('error', '알 수 없는 오류')}")
            
    except Exception as e:
        print(f"💥 예외 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integrated_crawling() 