import pymupdf4llm
import pymupdf
from pathlib import Path
from glob import glob
import os, re, sys, time, warnings, contextlib, csv
from tabulate import tabulate
from multiprocessing import Pool, cpu_count
warnings.filterwarnings("ignore")

@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

def convert_pdf_file(pdf_path, output_path, original_filename=None):
    """
    주어진 PDF 파일에서 텍스트를 추출합니다.
    """

    # 페이지별로 처리하여 더 정확한 페이지 번호 매핑
    with suppress_stderr():
        doc = pymupdf.open(pdf_path)
    
    all_content = []

    pdf_name = Path(pdf_path).stem
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 페이지 헤더 추가
        all_content.append(f"\n---\n**아래는 {pdf_name} 파일의 {page_num + 1}페이지 내용입니다.**\n\n")
        
        # 페이지별 마크다운 변환
        page_md = pymupdf4llm.to_markdown(pdf_path, pages=[page_num])
        
        # 구조 요소 변환
        page_md = re.sub(r'^(제\s*\d+\s*장[^\n]*)', r'## \1', page_md, flags=re.MULTILINE)
        page_md = re.sub(r'^(제\s*\d+\s*절[^\n]*)', r'### \1', page_md, flags=re.MULTILINE)
        page_md = re.sub(r'^(제\s*\d+\s*조[^\n]*)', r'#### \1', page_md, flags=re.MULTILINE)
        
        all_content.append(page_md)
    
    doc.close()
    
    final_content = ''.join(all_content)
     
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    print(f"변환 완료: {output_path}")
    return final_content
