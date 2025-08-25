import os
import tempfile
import pandas as pd
import docx 
import shutil

from .hwp2txt import convert_hwp_file
from .pdf_to_md_txt import convert_pdf_file
from .docx_to_md_txt import convert_docx_file

def convert2txt(firebase_path, output_folder, bucket, filename_mapping=None):
    """
    지정된 폴더 내의 HWP, PDF, DOCX, TXT 파일을 TXT로 변환합니다.
    
    Args:
        folder_path (str): 변환할 파일들이 있는 폴더 경로 - firebase storage 
        output_folder (str, optional): 변환된 TXT 파일을 저장할 폴더
    
    Returns:
        None
    """
    blobs = bucket.list_blobs(prefix=firebase_path)
    os.makedirs(output_folder, exist_ok=True)
    filename_mapping = filename_mapping or {}

    def get_output_path(file_name):
        base_name = os.path.splitext(file_name)[0]
        original_name = filename_mapping.get(file_name, file_name)
        original_base = os.path.splitext(original_name)[0]
        return os.path.join(output_folder, f"{original_base}.txt")

    for blob in blobs:
        file_name = os.path.basename(blob.name)
        lower_name = file_name.lower()

        if not lower_name.endswith(('.pdf', '.docx', '.hwp', '.txt')):
            continue
        if not file_name or file_name.startswith('.'):
            continue

        output_path = get_output_path(file_name)
        if os.path.exists(output_path):
            print(f"[스킵됨] 이미 존재: {output_path}")
            continue

        try:
            temp_path = os.path.join(tempfile.gettempdir(), file_name)
            blob.download_to_filename(temp_path)
            original_name = filename_mapping.get(file_name, file_name)

            if lower_name.endswith('.hwp'):
                convert_hwp_file(temp_path, output_path, original_filename=original_name)
            elif lower_name.endswith('.pdf'):
                convert_pdf_file(temp_path, output_path, original_filename=original_name)
            elif lower_name.endswith('.docx'):
                convert_docx_file(temp_path, output_path, original_filename=original_name)
            elif lower_name.endswith('.txt'):
                try:
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    base_name = os.path.splitext(filename_mapping.get(file_name, file_name))[0]
                    with open(output_path, 'w', encoding='utf-8') as out:
                        out.write(f"headline: {base_name}\ncontent:\n{text}")
                    print(f"[TXT 변환] {temp_path} → {output_path}")
                except Exception as e:
                    print(f"[오류] {file_name} 변환 실패: {e}")
        except Exception as e:
            print(f"[오류] {file_name} 처리 실패: {e}")

    print("모든 파일 변환 완료")


# def convert_docx(file_path, output_path, original_filename):
#     """DOCX 파일을 TXT로 변환합니다."""
#     try:
#         doc = docx.Document(file_path)
#         text = '\n'.join([para.text for para in doc.paragraphs])
#         if original_filename:
#             headline = os.path.splitext(original_filename)[0]
#         else:
#             headline = os.path.splitext(os.path.basename(file_path))[0]
#         with open(output_path, 'w', encoding='utf-8') as f:
#             f.write(f"headline: {headline}\ncontent:\n{text}")
#         print(f"[DOCX 변환] {file_path} → {output_path}")
#     except Exception as e:
#         print(f"[오류] {file_path} 변환 실패: {e}")

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