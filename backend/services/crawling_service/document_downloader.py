#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한성대학교 문서 다운로더
Document URLs에서 파일들을 다운로드하여 input 폴더에 저장
특정 확장자의 문서 파일만 저장
"""

import os
import requests
import time
import re
from urllib.parse import urlparse, unquote
from pathlib import Path
import logging
from typing import List, Optional
import hashlib
import mimetypes

class DocumentDownloader:
    def __init__(self, input_folder: str, 
                domain: str = "hansung", delay: float = 1.0):
        """
        문서 다운로더 초기화
        
        Args:
            input_folder: 다운로드할 파일들을 저장할 기본 폴더
            domain: 도메인 이름 (폴더명에 사용)
            delay: 요청 간 지연 시간 (초)
        """
        self.input_folder = Path(input_folder)
        self.domain = domain
        self.delay = delay
        self.download_folder = self.input_folder / f"{domain}_document"
        
        # 허용할 문서 확장자 목록
        self.allowed_extensions = {'.pdf', '.docx', '.doc', '.hwp', '.txt', '.hwpx', '.word'}
        
        # 중복 파일 기록을 위한 파일 경로
        self.duplicate_log_file = self.download_folder / "duplicate_files_log.txt"
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{domain}_download.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # 다운로드 폴더 생성
        self.download_folder.mkdir(parents=True, exist_ok=True)
        
        # 중복 파일 로그 초기화
        if not self.duplicate_log_file.exists():
            with open(self.duplicate_log_file, 'w', encoding='utf-8') as f:
                f.write("중복 파일 처리 기록\n")
                f.write("=" * 50 + "\n")
                f.write("형식: [날짜시간] 원본파일명 -> 새파일명 (원본크기 vs 새크기) URL\n\n")
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 다운로드 통계
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'filtered_out': 0,  # 확장자 필터링으로 제외된 파일 수
            'duplicates_renamed': 0  # 크기가 달라서 번호를 추가한 파일 수
        }

    def load_urls_from_file(self, file_path: str) -> List[str]:
        """
        파일에서 URL 목록을 로드
        
        Args:
            file_path: URL 목록이 있는 파일 경로
            
        Returns:
            URL 목록
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            self.logger.info(f"총 {len(urls)}개의 URL을 로드했습니다.")
            return urls
        except Exception as e:
            self.logger.error(f"URL 파일 로드 실패: {e}")
            return []

    def get_filename_from_url(self, url: str, content_disposition: Optional[str] = None) -> str:
        """
        URL과 Content-Disposition 헤더에서 파일명 추출
        
        Args:
            url: 다운로드 URL
            content_disposition: Content-Disposition 헤더 값
            
        Returns:
            파일명
        """
        filename = None
        
        # Content-Disposition 헤더에서 파일명 추출 시도
        if content_disposition:
            # filename*=UTF-8''... 형식 처리
            if "filename*=" in content_disposition:
                match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition)
                if match:
                    filename = unquote(match.group(1))
            # filename="..." 형식 처리
            elif "filename=" in content_disposition:
                match = re.search(r'filename="([^"]+)"', content_disposition)
                if not match:
                    match = re.search(r'filename=([^;]+)', content_disposition)
                if match:
                    filename = unquote(match.group(1).strip('"'))
        
        # URL에서 파일명 추출 시도
        if not filename:
            parsed_url = urlparse(url)
            path = parsed_url.path
            
            # URL 경로에서 파일명 추출
            if path and '/' in path:
                potential_filename = path.split('/')[-1]
                if '.' in potential_filename:
                    filename = unquote(potential_filename)
        
        # 파일명이 없으면 URL 해시로 생성
        if not filename:
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"document_{url_hash}.bin"
        
        # 파일명이 여전히 인코딩되어 있다면 추가 디코딩 시도
        if filename and ('_' in filename and len(filename) > 50):
            try:
                # URL 인코딩된 문자열을 바이트로 변환 후 UTF-8로 디코딩
                # _EC_B5_90 형태를 %EC%B5%90 형태로 변환
                encoded_filename = filename.replace('_', '%')
                if encoded_filename.startswith('%'):
                    decoded_filename = unquote(encoded_filename)
                    # 디코딩이 성공하고 한글이 포함되어 있으면 사용
                    if decoded_filename != encoded_filename and any('\uac00' <= c <= '\ud7af' for c in decoded_filename):
                        filename = decoded_filename
            except:
                pass
        
        # 파일명 정리 (특수문자 제거)
        if filename:
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            # 파일명이 너무 길면 자르기 (확장자 보존)
            if len(filename) > 100:
                name_part, ext_part = os.path.splitext(filename)
                filename = name_part[:90] + ext_part
        
        return filename

    def is_document_file(self, file_path: Path) -> bool:
        """
        파일이 허용된 문서 확장자인지 확인
        
        Args:
            file_path: 확인할 파일 경로
            
        Returns:
            문서 파일 여부
        """
        # 파일 확장자 확인
        file_extension = file_path.suffix.lower()
        
        if file_extension in self.allowed_extensions:
            return True
        
        # 명시적으로 제외할 확장자들
        excluded_extensions = {'.pptx', '.ppt', '.xlsx', '.xls', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg'}
        if file_extension in excluded_extensions:
            return False
        
        # MIME 타입으로도 확인
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            # 문서 관련 MIME 타입들 (PowerPoint 제외)
            document_mime_types = {
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.hancom.hwp',
                'text/plain',
                'application/x-hwp'
            }
            
            # PowerPoint 관련 MIME 타입 제외
            excluded_mime_types = {
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            
            if mime_type in excluded_mime_types:
                return False
            
            if mime_type in document_mime_types:
                return True
        
        # 파일 내용의 시작 바이트로 확인 (매직 넘버)
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # 더 많은 바이트 읽기
                
            # PDF 파일 확인
            if header.startswith(b'%PDF'):
                return True
            
            # HWP 파일 확인
            if header.startswith(b'\xd0\xcf\x11\xe0') or header.startswith(b'HWP'):
                return True
            
            # ZIP 기반 파일들 확인 (docx, hwpx 등)
            if header.startswith(b'PK\x03\x04'):
                # ZIP 파일이지만 확장자로 더 정확히 판단
                file_extension = file_path.suffix.lower()
                # docx, hwpx만 허용하고 pptx는 제외
                allowed_zip_extensions = {'.docx', '.hwpx'}
                if file_extension in allowed_zip_extensions:
                    return True
                else:
                    return False
                
        except Exception:
            pass
        
        return False

    def download_file(self, url: str) -> bool:
        """
        단일 파일 다운로드
        
        Args:
            url: 다운로드할 URL
            
        Returns:
            다운로드 성공 여부
        """
        temp_file_path = None
        try:
            self.logger.info(f"다운로드 시작: {url}")
            
            # HEAD 요청으로 파일 정보 확인
            try:
                head_response = self.session.head(url, timeout=30, allow_redirects=True)
                content_disposition = head_response.headers.get('Content-Disposition')
                content_length = head_response.headers.get('Content-Length')
                
                if content_length:
                    file_size = int(content_length)
                    if file_size > 100 * 1024 * 1024:  # 100MB 제한
                        self.logger.warning(f"파일 크기가 너무 큽니다 ({file_size} bytes): {url}")
                        return False
            except:
                content_disposition = None
            
            # 파일명 결정
            filename = self.get_filename_from_url(url, content_disposition)
            file_path = self.download_folder / filename
            
            # 임시 파일로 다운로드
            temp_file_path = self.download_folder / f"temp_{filename}"
            
            # 파일 다운로드
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            # 임시 파일에 저장
            with open(temp_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 파일이 문서 파일인지 확인
            if self.is_document_file(temp_file_path):
                # 임시 파일 크기 확인
                temp_file_size = temp_file_path.stat().st_size
                
                # 중복 파일명 처리 (크기 비교)
                final_file_path, is_renamed = self.get_unique_filename(file_path, temp_file_size)
                
                if is_renamed:
                    # 크기가 달라서 새 파일명으로 저장
                    original_size = file_path.stat().st_size if file_path.exists() else 0
                    temp_file_path.rename(final_file_path)
                    
                    # 중복 파일 로그 기록
                    self.log_duplicate_file(file_path, final_file_path, original_size, temp_file_size, url, "renamed")
                    
                    self.logger.info(f"다운로드 완료 (크기 다름, 새 파일명): {final_file_path.name} ({temp_file_size} bytes)")
                    self.stats['duplicates_renamed'] += 1
                    
                elif final_file_path.exists() and final_file_path.stat().st_size == temp_file_size:
                    # 같은 크기의 파일이 이미 존재함
                    temp_file_path.unlink()  # 임시 파일 삭제
                    
                    # 중복 파일 로그 기록 (건너뜀)
                    self.log_duplicate_file(file_path, file_path, temp_file_size, temp_file_size, url, "skipped")
                    
                    self.logger.info(f"파일이 이미 존재합니다 (같은 크기): {filename}")
                    self.stats['skipped'] += 1
                    
                else:
                    # 새 파일 저장
                    temp_file_path.rename(final_file_path)
                    self.logger.info(f"다운로드 완료 (문서 파일): {final_file_path.name} ({temp_file_size} bytes)")
                    self.stats['success'] += 1
                    
                return True
            else:
                # 문서 파일이 아니면 삭제
                temp_file_path.unlink()
                self.logger.info(f"문서 파일이 아니므로 제외: {filename}")
                self.stats['filtered_out'] += 1
                return False
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"다운로드 실패 (네트워크 오류): {url} - {e}")
            self.stats['failed'] += 1
            if temp_file_path and temp_file_path.exists():
                temp_file_path.unlink()
            return False
        except Exception as e:
            self.logger.error(f"다운로드 실패 (기타 오류): {url} - {e}")
            self.stats['failed'] += 1
            if temp_file_path and temp_file_path.exists():
                temp_file_path.unlink()
            return False

    def download_all(self, urls: List[str]) -> None:
        """
        모든 URL에서 파일 다운로드
        
        Args:
            urls: 다운로드할 URL 목록
        """
        self.stats['total'] = len(urls)
        self.logger.info(f"총 {len(urls)}개 파일 다운로드를 시작합니다.")
        self.logger.info(f"저장 폴더: {self.download_folder}")
        self.logger.info(f"허용 확장자: {', '.join(self.allowed_extensions)}")
        
        for i, url in enumerate(urls, 1):
            self.logger.info(f"진행률: {i}/{len(urls)} ({i/len(urls)*100:.1f}%)")
            
            success = self.download_file(url)
            
            # 지연 시간
            if i < len(urls):  # 마지막 파일이 아닌 경우에만 지연
                time.sleep(self.delay)
        
        # 최종 통계 출력
        self.print_stats()

    def print_stats(self) -> None:
        """다운로드 통계 출력"""
        self.logger.info("=" * 50)
        self.logger.info("다운로드 완료!")
        self.logger.info(f"총 파일 수: {self.stats['total']}")
        self.logger.info(f"성공 (문서 파일): {self.stats['success']}")
        self.logger.info(f"실패: {self.stats['failed']}")
        self.logger.info(f"건너뜀 (이미 존재): {self.stats['skipped']}")
        self.logger.info(f"제외됨 (문서 파일 아님): {self.stats['filtered_out']}")
        self.logger.info(f"중복 처리 (크기 다름): {self.stats['duplicates_renamed']}")
        self.logger.info(f"저장 폴더: {self.download_folder}")
        self.logger.info(f"허용 확장자: {', '.join(self.allowed_extensions)}")
        if self.stats['duplicates_renamed'] > 0 or self.stats['skipped'] > 0:
            self.logger.info(f"중복 파일 로그: {self.duplicate_log_file}")
        self.logger.info("=" * 50)

    def get_unique_filename(self, file_path: Path, new_file_size: int) -> tuple[Path, bool]:
        """
        중복 파일명 처리 - 크기가 다르면 번호를 추가한 새 파일명 생성
        
        Args:
            file_path: 원본 파일 경로
            new_file_size: 새 파일의 크기
            
        Returns:
            (최종 파일 경로, 크기가 달라서 이름을 변경했는지 여부)
        """
        if not file_path.exists():
            return file_path, False
        
        # 기존 파일 크기 확인
        existing_file_size = file_path.stat().st_size
        
        # 크기가 같으면 기존 파일 유지
        if existing_file_size == new_file_size:
            return file_path, False
        
        # 크기가 다르면 새로운 파일명 생성
        base_name = file_path.stem
        extension = file_path.suffix
        parent_dir = file_path.parent
        
        counter = 1
        while True:
            new_filename = f"{base_name}_{counter}{extension}"
            new_file_path = parent_dir / new_filename
            
            if not new_file_path.exists():
                return new_file_path, True
            
            # 새 파일 경로도 존재하면 크기 비교
            existing_size = new_file_path.stat().st_size
            if existing_size == new_file_size:
                return new_file_path, False
            
            counter += 1
            
            # 무한 루프 방지
            if counter > 100:
                break
        
        return file_path, False

    def log_duplicate_file(self, original_path: Path, new_path: Path, original_size: int, new_size: int, url: str, action: str = "renamed"):
        """
        중복 파일 처리 기록을 로그 파일에 저장
        
        Args:
            original_path: 원본 파일 경로
            new_path: 새 파일 경로 (action이 "skipped"인 경우 original_path와 같음)
            original_size: 원본 파일 크기
            new_size: 새 파일 크기
            url: 다운로드 URL
            action: 처리 방식 ("renamed" 또는 "skipped")
        """
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if action == "renamed":
                log_entry = (
                    f"[{timestamp}] 크기 다름으로 새 파일명 생성\n"
                    f"  원본: {original_path.name} ({original_size:,} bytes)\n"
                    f"  새파일: {new_path.name} ({new_size:,} bytes)\n"
                    f"  URL: {url}\n\n"
                )
            elif action == "skipped":
                log_entry = (
                    f"[{timestamp}] 같은 크기로 건너뜀\n"
                    f"  파일명: {original_path.name} ({original_size:,} bytes)\n"
                    f"  URL: {url}\n\n"
                )
            else:
                log_entry = (
                    f"[{timestamp}] 알 수 없는 처리: {action}\n"
                    f"  파일명: {original_path.name}\n"
                    f"  URL: {url}\n\n"
                )
            
            with open(self.duplicate_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            self.logger.warning(f"중복 파일 로그 기록 실패: {e}")

def main():
    """메인 함수"""
    # 설정
    url_file = Path.joinpath(Path(__file__).parent.parent.parent, "data/crawling/20250526_0521_hansung_ac_kr_cse_cse/document_urls_20250526_0521.txt")
    
    # 다운로더 생성
    downloader = DocumentDownloader(
        input_folder=Path.joinpath(Path(__file__).parent.parent.parent, "data/crawling/20250526_0521_hansung_ac_kr_cse_cse"),
        domain="hansung_CSE",
        delay=1.0  # 1초 지연
    )
    
    # URL 목록 로드
    urls = downloader.load_urls_from_file(url_file)
    
    if not urls:
        print("다운로드할 URL이 없습니다.")
        return
    
    # 다운로드 실행
    try:
        downloader.download_all(urls)
    except KeyboardInterrupt:
        print("\n다운로드가 중단되었습니다.")
        downloader.print_stats()

if __name__ == "__main__":
    main() 