import os
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import logging

# 로컬 모듈 임포트
from Jina_crawling import batch_jina_crawling, jina_crawling
from artclView_Crawling import Crawler, read_urls_from_file

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("html_structuring.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("html_structuring")

def filter_urls_by_patterns(urls, patterns):
    """URL 리스트에서 특정 패턴이 포함된 URL을 필터링하는 함수
    
    Args:
        urls: URL 리스트
        patterns: 필터링할 패턴 리스트
        
    Returns:
        tuple: (패턴에 매칭되는 URL 리스트, 매칭되지 않는 URL 리스트)
    """
    matched_urls = []
    unmatched_urls = []
    
    for url in urls:
        if any(pattern in url for pattern in patterns):
            matched_urls.append(url)
        else:
            unmatched_urls.append(url)
    
    return matched_urls, unmatched_urls

def create_temp_url_file(urls, prefix="temp_urls"):
    """URL 리스트를 임시 파일로 저장하는 함수
    
    Args:
        urls: URL 리스트
        prefix: 파일명 접두사
        
    Returns:
        str: 생성된 임시 파일 경로
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = Path(__file__).parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    temp_file_path = temp_dir / f"{prefix}_{timestamp}.txt"
    
    with open(temp_file_path, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(f"{url}\n")
    
    return str(temp_file_path)

def cleanup_temp_file(file_path):
    """임시 파일을 삭제하는 함수
    
    Args:
        file_path: 삭제할 파일 경로
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"임시 파일 삭제 완료: {file_path}")
    except Exception as e:
        logger.warning(f"임시 파일 삭제 실패: {file_path}, 오류: {e}")

def integrated_crawling(url_list, output_base_dir=None, max_workers=5, delay_range=(0.5, 1.5), verbose=True):
    """통합 크롤링 함수
    
    Args:
        url_list: 크롤링할 URL 파일 경로
        output_base_dir: 결과를 저장할 기본 디렉토리 경로 (None이면 기본 경로 사용)
        max_workers: Jina 크롤링 시 동시 작업자 수
        delay_range: Jina 크롤링 시 요청 간 지연 시간 범위
        verbose: 상세 로그 출력 여부
        
    Returns:
        dict: 크롤링 결과 정보
    """
    start_time = datetime.now()
    logger.info(f"통합 크롤링 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 기본 저장 경로 설정
    if output_base_dir is None:
        output_base_dir = Path(__file__).parent.parent.parent / "data" / "crawling" / "integrated_crawling"
    else:
        output_base_dir = Path(output_base_dir)
    
    # 타임스탬프가 포함된 폴더 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_base_dir = output_base_dir / f"crawling_{timestamp}"
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"크롤링 결과 저장 기본 경로: {output_base_dir}")

    # URL 리스트 처리
    if isinstance(url_list, str):
        if os.path.exists(url_list):
            urls = read_urls_from_file(url_list)
            logger.info(f"파일에서 {len(urls)}개 URL 읽기 완료: {url_list}")
        else:
            logger.error(f"URL 파일을 찾을 수 없습니다: {url_list}")
            return {"error": "URL 파일을 찾을 수 없습니다"}
    else:
        logger.error("잘못된 URL 입력 형식입니다")
        return {"error": "잘못된 URL 입력 형식입니다"}
    
    if not urls:
        logger.error("크롤링할 URL이 없습니다")
        return {"error": "크롤링할 URL이 없습니다"}
    
    # 중복 제거
    unique_urls = list(set(urls))
    logger.info(f"중복 제거 후 {len(unique_urls)}개 URL")
    
    # URL 패턴별 분류
    target_patterns = ['artclView.do', 'artclList.do']
    artcl_urls, jina_urls = filter_urls_by_patterns(unique_urls, target_patterns)
    
    logger.info(f"URL 분류 완료:")
    logger.info(f"  - artclView/artclList 패턴: {len(artcl_urls)}개")
    logger.info(f"  - 일반 Jina 크롤링: {len(jina_urls)}개")
    
    results = {
        "start_time": start_time,
        "output_base_dir": str(output_base_dir),
        "total_urls": len(unique_urls),
        "artcl_urls_count": len(artcl_urls),
        "jina_urls_count": len(jina_urls),
        "artcl_results": [],
        "jina_results": [],
        "errors": []
    }
    
    # 1. artclView/artclList URL 크롤링 (artclView_Crawling.py 사용)
    if artcl_urls:
        logger.info(f"\n=== artclView/artclList URL 크롤링 시작 ({len(artcl_urls)}개) ===")
        try:
            # artclView 크롤러용 저장 경로
            artcl_output_dir = output_base_dir / "artclView_crawling"
            
            crawler = Crawler(urls=artcl_urls, output_base_dir=str(artcl_output_dir))
            saved_files, saved_attachments = crawler.crawl_multiple_pages()

            results["artcl_results"] = {
                "saved_files": saved_files,
                "saved_attachments": saved_attachments,
                "success_count": len(saved_files),
                "attachment_count": len(saved_attachments),
                "output_dir": str(artcl_output_dir)
            }
            
            logger.info(f"artclView/artclList 크롤링 완료: {len(saved_files)}개 파일 저장")
            
        except Exception as e:
            error_msg = f"artclView/artclList 크롤링 오류: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
        finally:
            # 크롤러 정리
            if 'crawler' in locals():
                try:
                    crawler.driver.quit()
                except:
                    pass
    
    # 2. 일반 URL Jina 크롤링
    if jina_urls:
        logger.info(f"\n=== Jina 크롤링 시작 ({len(jina_urls)}개) ===")
        try:
            # Jina 크롤러용 저장 경로
            jina_output_dir = output_base_dir / "jina_crawling"
            
            # 임시 URL 파일 생성
            temp_url_file = create_temp_url_file(jina_urls, "jina_urls")
            
            # Jina 배치 크롤링 실행
            jina_saved_files = batch_jina_crawling(
                url_list_file=temp_url_file,
                output_dir=str(jina_output_dir),
                max_workers=max_workers,
                delay_range=delay_range,
                verbose=verbose
            )
            
            results["jina_results"] = {
                "saved_files": jina_saved_files,
                "success_count": len(jina_saved_files),
                "output_dir": str(jina_output_dir)
            }
            
            logger.info(f"Jina 크롤링 완료: {len(jina_saved_files)}개 파일 저장")
            
            # 임시 파일 정리
            cleanup_temp_file(temp_url_file)
            
        except Exception as e:
            error_msg = f"Jina 크롤링 오류: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)
    
    # 최종 결과 정리
    end_time = datetime.now()
    execution_time = end_time - start_time
    
    results.update({
        "end_time": end_time,
        "execution_time": str(execution_time),
        "total_success_count": (
            results.get("artcl_results", {}).get("success_count", 0) + 
            results.get("jina_results", {}).get("success_count", 0)
        )
    })
    
    logger.info(f"\n=== 통합 크롤링 완료 ===")
    logger.info(f"총 실행 시간: {execution_time}")
    logger.info(f"총 성공한 파일: {results['total_success_count']}개")
    logger.info(f"artclView/artclList: {results.get('artcl_results', {}).get('success_count', 0)}개")
    logger.info(f"Jina 크롤링: {results.get('jina_results', {}).get('success_count', 0)}개")
    
    if results["errors"]:
        logger.warning(f"발생한 오류: {len(results['errors'])}개")
        for error in results["errors"]:
            logger.warning(f"  - {error}")
    
    return results

def crawl_from_file(url_file_path, output_base_dir=None, **kwargs):
    """파일에서 URL을 읽어 통합 크롤링을 수행하는 편의 함수
    
    Args:
        url_file_path: URL 목록이 저장된 파일 경로
        output_base_dir: 결과를 저장할 기본 디렉토리 경로
        **kwargs: integrated_crawling 함수에 전달할 추가 인자
        
    Returns:
        dict: 크롤링 결과 정보
    """
    return integrated_crawling(url_file_path, output_base_dir=output_base_dir, **kwargs)

if __name__ == "__main__":
    # 테스트 실행 예시
    
    # 1. 파일에서 URL 읽어서 크롤링 (테스트 모드)
    url_file_path = Path(__file__).parent.parent.parent.parent / "data/crawling/20250526_0412_hansung_ac_kr_sites_hansung/page_urls_20250526_0412.txt"
    
    # 사용자 지정 저장 경로 (예시)
    custom_output_dir = Path(__file__).parent.parent.parent / "data" / "crawling" / "20250526_0412_hansung_ac_kr_sites_hansung"
    
    if url_file_path.exists():
        logger.info("파일 기반 테스트 크롤링 시작")
        results = crawl_from_file(
            str(url_file_path),
            output_base_dir=str(custom_output_dir),
            max_workers=3,
            delay_range=(1.0, 2.0),
            verbose=True
        )
        print(f"테스트 결과: {results['total_success_count']}개 파일 생성")
        print(f"저장 위치: {results.get('output_base_dir', 'N/A')}")
    else:
        logger.warning(f"테스트 URL 파일을 찾을 수 없습니다: {url_file_path}")

        logger.info("URL 리스트 기반 테스트 크롤링 시작")
        results = crawl_from_file(
            str(url_file_path),
            output_base_dir=str(custom_output_dir),
            max_workers=2,
            verbose=True
        )
        print(f"테스트 결과: {results['total_success_count']}개 파일 생성")
        print(f"저장 위치: {results.get('output_base_dir', 'N/A')}")
