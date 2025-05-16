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

def convert_hwp_file(file_path, output_path):
    """
    HWP 파일을 output_path에 .txt로 저장하는 외부 호출용 함수
    """
    text = get_hwp_text(file_path)

    cleaned_text = re.sub(r'[^\x00-\x7F\uAC00-\uD7AF]', '', text)
    headline = os.path.splitext(os.path.basename(file_path))[0]
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"headline: {headline}\ncontent:\n{cleaned_text}")

    print(f"[HWP→TXT] {file_path} → {output_path}")