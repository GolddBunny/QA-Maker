import os
import olefile
import zlib
import struct
import re

def get_hwp_text(filename):
    """
    주어진 HWP 파일에서 텍스트를 추출합니다.
    
    Args:
        filename (str): HWP 파일의 경로
    
    Returns:
        str: 추출된 텍스트
    """
    f = olefile.OleFileIO(filename)
    dirs = f.listdir()

    # HWP 파일의 유효성 검사
    if ["FileHeader"] not in dirs or ["\x05HwpSummaryInformation"] not in dirs:
        raise Exception("Not Valid HWP.")

    # FileHeader 스트림 읽기
    header = f.openstream("FileHeader")
    header_data = header.read()
    is_compressed = (header_data[36] & 1) == 1

    # BodyText 섹션 찾기
    nums = []
    for d in dirs:
        if d[0] == "BodyText":
            nums.append(int(d[1][len("Section"):]))
    sections = ["BodyText/Section" + str(x) for x in sorted(nums)]

    # 섹션 반복하여 텍스트 추출
    text = ""
    for section in sections:
        bodytext = f.openstream(section)
        data = bodytext.read()

        # 압축된 데이터가 있으면 압축 풀기
        if is_compressed:
            unpacked_data = zlib.decompress(data, -15)
        else:
            unpacked_data = data

        # 섹션 텍스트 추출
        section_text = ""
        i = 0
        size = len(unpacked_data)
        while i < size:
            header = struct.unpack_from("<I", unpacked_data, i)[0]
            rec_type = header & 0x3ff
            rec_len = (header >> 20) & 0xfff

            # 텍스트 레코드 (rec_type 67) 처리
            if rec_type == 67:
                try:
                    rec_data = unpacked_data[i + 4:i + 4 + rec_len]
                    # 디코딩할 때 문제가 생기지 않도록 처리
                    decoded_text = rec_data.decode('utf-16', errors='ignore')
                    section_text += decoded_text
                    section_text += "\n"
                except UnicodeDecodeError:
                    # 유효하지 않은 텍스트는 건너뛰기
                    pass

            i += 4 + rec_len

        text += section_text
        text += "\n"

    return text

def convert_hwp_files_in_folder(folder_path):
    """
    주어진 폴더 내의 모든 .hwp 파일을 텍스트 파일로 변환합니다.
    
    Args:
        folder_path (str): 변환할 파일들이 있는 폴더 경로
    
    Returns:
        None
    """
    # 폴더 내 모든 파일 확인
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        # .hwp 파일만 처리
        if file_name.lower().endswith('.hwp'):
            try:
                # HWP 파일에서 텍스트 추출
                text = get_hwp_text(file_path)

                # 텍스트 정리 (ASCII 문자와 한글(가-힣)만 남기고 나머지 문자 제거)
                cleaned_text = re.sub(r'[^\x00-\x7F\uAC00-\uD7AF]', '', text)

                # 파일 경로에서 .hwp 파일의 이름을 .txt로 변환하여 저장할 경로 지정
                txt_file_name = file_name.replace('.hwp', '.txt')
                txt_file_path = os.path.join(folder_path, txt_file_name)

                # 텍스트를 .txt 파일로 저장
                with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
                    txt_file.write(cleaned_text)

                print(f"[변환 성공] {file_name} → {txt_file_path}")
            except Exception as e:
                print(f"[오류] {file_name} 변환 실패: {e}")

# 폴더 경로가 존재하는지 확인, 없으면 생성
folder_path = './hwp_test_hwp'
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# 예시로 './hsu_texts_original' 폴더 내 모든 .hwp 파일을 변환
convert_hwp_files_in_folder(folder_path)

print("모든 파일 변환 완료!")