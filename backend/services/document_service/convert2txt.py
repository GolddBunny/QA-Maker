import os
import subprocess
import fitz  
import pandas as pd
import docx 
import shutil

def convert2txt(folder_path, output_folder=None):
    """
    지정된 폴더 내의 HWP, PDF, DOCX, Excel 파일을 TXT로 변환합니다.
    
    Args:
        folder_path (str): 변환할 파일들이 있는 폴더 경로
        output_folder (str, optional): 변환된 TXT 파일을 저장할 폴더 (기본값: 원본 폴더에 저장)
    
    Returns:
        None
    """
    if output_folder is None:
        output_folder = folder_path  # 기본적으로 원본 폴더에 저장

    os.makedirs(output_folder, exist_ok=True)

    # 폴더 내 모든 파일 확인
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        # 파일 확장자 확인 및 변환
        if file_name.lower().endswith('.hwp'):
            convert_hwp(file_path, output_folder)
        elif file_name.lower().endswith('.pdf'):
            convert_pdf(file_path, output_folder)
        elif file_name.lower().endswith('.docx'):
            convert_docx(file_path, output_folder)
        elif file_name.lower().endswith(('.xls', '.xlsx')):
            convert_excel(file_path, output_folder)
        elif file_name.lower().endswith('.txt'):
            # .txt 파일은 변환 없이 그대로 저장
            txt_path = os.path.join(output_folder, os.path.basename(file_path))
            shutil.copy(file_path, txt_path)
            print(f"[TXT 복사] {file_path} → {txt_path}")

    print("모든 파일 변환 완료!")


def convert_hwp(file_path, output_folder):
    """HWP 파일을 TXT로 변환"""
    txt_path = os.path.join(output_folder, os.path.basename(file_path).replace('.hwp', '.txt'))
    try:
        result = subprocess.run(['hwp5txt', file_path], capture_output=True, text=True, encoding='utf-8')
        text = result.stdout
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        print(f"[HWP 변환] {file_path} → {txt_path}")
    except Exception as e:
        print(f"[오류] {file_path} 변환 실패: {e}")

def convert_pdf(file_path, output_folder):
    """PDF 파일을 TXT로 변환"""
    txt_path = os.path.join(output_folder, os.path.basename(file_path).replace('.pdf', '.txt'))
    try:
        doc = fitz.open(file_path)
        text = '\n'.join([page.get_text("text") for page in doc])
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        print(f"[PDF 변환] {file_path} → {txt_path}")
    except Exception as e:
        print(f"[오류] {file_path} 변환 실패: {e}")

def convert_docx(file_path, output_folder):
    """DOCX 파일을 TXT로 변환"""
    txt_path = os.path.join(output_folder, os.path.basename(file_path).replace('.docx', '.txt'))
    try:
        doc = docx.Document(file_path)
        text = '\n'.join([para.text for para in doc.paragraphs])
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        print(f"[DOCX 변환] {file_path} → {txt_path}")
    except Exception as e:
        print(f"[오류] {file_path} 변환 실패: {e}")

def convert_excel(file_path, output_folder):
    """Excel 파일을 TXT로 변환"""
    txt_path = os.path.join(output_folder, os.path.basename(file_path).replace('.xlsx', '.txt').replace('.xls', '.txt'))
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        text = df.to_csv(sep='\t', index=False)
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        print(f"[Excel 변환] {file_path} → {txt_path}")
    except Exception as e:
        print(f"[오류] {file_path} 변환 실패: {e}")