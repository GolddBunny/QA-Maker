import os
import pandas as pd
import docx 
import shutil

from .hwp2txt import convert_hwp_file
from .pdf2txt import extract_text_and_tables


def convert2txt(folder_path, output_folder):
    """
    지정된 폴더 내의 HWP, PDF, DOCX, Excel 파일을 TXT로 변환합니다.
    
    Args:
        folder_path (str): 변환할 파일들이 있는 폴더 경로
        output_folder (str, optional): 변환된 TXT 파일을 저장할 폴더 (기본값: 원본 폴더에 저장)
    
    Returns:
        None
    """

    os.makedirs(output_folder, exist_ok=True)

    def get_output_path(file_name):
        base_name = os.path.splitext(file_name)[0]
        return os.path.join(output_folder, f"{base_name}.txt")

    # 폴더 내 모든 파일 확인
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        lower_name = file_name.lower()
        output_path = get_output_path(file_name)

        # 이미 변환된 파일이 있다면 스킵
        if os.path.exists(output_path):
            print(f"[스킵됨] 이미 존재: {output_path}")
            continue

        try:
            if lower_name.endswith('.hwp'):
                convert_hwp_file(file_path, output_path)

            elif lower_name.endswith('.pdf'):
                extract_text_and_tables(file_path, output_path)

            elif lower_name.endswith('.docx'):
                convert_docx(file_path, output_path)

            elif lower_name.endswith('.txt'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    base_name = os.path.splitext(file_name)[0]
                    with open(output_path, 'w', encoding='utf-8') as out:
                        out.write(f"headline: {base_name}\ncontent:\n{text}")
                    print(f"[TXT 변환] {file_path} → {output_path}")
                except Exception as e:
                    print(f"[오류] {file_name} 변환 실패: {e}")

        except Exception as e:
            print(f"[오류] {file_name} 처리 실패: {e}")

    print("모든 파일 변환 완료")


def convert_docx(file_path, output_path):
    """DOCX 파일을 TXT로 변환합니다."""
    try:
        doc = docx.Document(file_path)
        text = '\n'.join([para.text for para in doc.paragraphs])
        headline = os.path.splitext(os.path.basename(file_path))[0]
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"headline: {headline}\ncontent:\n{text}")
        print(f"[DOCX 변환] {file_path} → {output_path}")
    except Exception as e:
        print(f"[오류] {file_path} 변환 실패: {e}")

# def convert_excel(file_path, output_folder):
#     """Excel 파일을 TXT로 변환"""
#     txt_path = os.path.join(output_folder, os.path.basename(file_path).replace('.xlsx', '.txt').replace('.xls', '.txt'))
#     try:
#         df = pd.read_excel(file_path, engine='openpyxl')
#         text = df.to_csv(sep='\t', index=False)
#         with open(txt_path, 'w', encoding='utf-8') as txt_file:
#             txt_file.write(text)
#         print(f"[Excel 변환] {file_path} → {txt_path}")
#     except Exception as e:
#         print(f"[오류] {file_path} 변환 실패: {e}")