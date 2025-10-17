import os
import olefile
import zlib
import struct
import re

def get_hwp_text(filename):
    """
    주어진 HWP 파일에서 섹션별 텍스트를 추출합니다.
    각 섹션을 페이지로 간주하여 반환합니다.
    
    Returns:
        list[str]: 섹션(페이지)별 텍스트 리스트
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
    pages = []   # 페이지별 텍스트를 리스트에 저장
    for section in sections:
        bodytext = f.openstream(section)
        data = bodytext.read()

        # 압축된 데이터가 있으면 압축 풀기
        if is_compressed:
            unpacked_data = zlib.decompress(data, -15)
        else:
            unpacked_data = data

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
                    decoded_text = rec_data.decode('utf-16', errors='ignore')
                    section_text += decoded_text + "\n"
                except UnicodeDecodeError:
                    pass

            i += 4 + rec_len

        pages.append(section_text.strip())

    return pages


def convert_hwp_file(file_path, output_path, original_filename):
    """
    HWP 파일을 output_path에 .txt로 저장하는 외부 호출용 함수
    페이지(섹션) 단위로 안내 문구 추가
    """
    pages = get_hwp_text(file_path)

    if original_filename:
        headline = os.path.splitext(original_filename)[0]
    else:
        headline = os.path.splitext(os.path.basename(file_path))[0]

    all_content = []

    for page_num, page_text in enumerate(pages, start=1):
        all_content.append(f"\n---\n**아래는 {headline} 파일의 {page_num}페이지 내용입니다.**\n\n")
        cleaned_text = re.sub(r'[^\x00-\x7F\uAC00-\uD7AF]', '', page_text)
        all_content.append(cleaned_text + "\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("".join(all_content))

    print(f"[HWP→TXT] {file_path} → {output_path}")

