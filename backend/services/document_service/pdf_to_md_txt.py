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

def has_meaningful_text(text, min_chars=70):
    """
    텍스트가 내용을 포함하고 있는지 확인
    """
    if not text or text.strip() == "":
        return False
    
    # 실제 문자 개수 계산 (공백, 특수문자 제외)
    actual_chars = re.sub(r'[^\w가-힣]', '', text)
    return len(actual_chars) >= min_chars

def extract_text_with_ocr(pdf_path, page_num):
    """
    OCR을 사용하여 PDF 페이지에서 텍스트 추출
    """
    try:
        doc = pymupdf.open(pdf_path)
        page = doc[page_num]
        
        # 페이지를 이미지로 변환 (해상도 높게)
        mat = pymupdf.Matrix(2.0, 2.0)  # 2배 확대
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        # PIL Image로 변환
        image = Image.open(io.BytesIO(img_data))
        
        # OCR 실행 (한국어 + 영어)
        custom_config = r'--oem 3 --psm 6 -l kor+eng'
        ocr_text = pytesseract.image_to_string(image, config=custom_config)
        
        doc.close()
        return ocr_text
        
    except Exception as e:
        print(f"OCR 처리 중 오류 발생: {e}")
        return ""
    
def convert_pdf_file(pdf_path, output_path, original_filename=None):
    """
    주어진 PDF 파일에서 텍스트를 추출합니다.
    텍스트가 추출되지 않는 경우 OCR 사용
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
        try:
            page_md = pymupdf4llm.to_markdown(pdf_path, pages=[page_num])
        except:
            page_md = ""

        # 텍스트가 충분하지 않으면 OCR 시도
        if not has_meaningful_text(page_md):
            print(f"  → {page_num + 1}페이지: 일반 텍스트 추출 실패, OCR 시도 중...")
            
            ocr_text = extract_text_with_ocr(pdf_path, page_num)
            
            if has_meaningful_text(ocr_text):
                # OCR 텍스트를 마크다운 형태로 정리
                page_md = ocr_text.strip()
                print(f"  → {page_num + 1}페이지: OCR로 텍스트 추출 성공")
            else:
                page_md = f"*이 페이지는 텍스트를 추출할 수 없습니다.*"
                print(f"  → {page_num + 1}페이지: 텍스트 추출 실패")
        else:
            print(f"  → {page_num + 1}페이지: 일반 텍스트 추출 성공")
        
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
