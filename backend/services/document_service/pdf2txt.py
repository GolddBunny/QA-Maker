
import pypdfium2 as pdfium
import camelot
import os
import glob
import re
import sys
import time
import warnings
import contextlib
from tabulate import tabulate
import csv 
from multiprocessing import Pool, cpu_count
# 모든 경고 메시지 숨기기
warnings.filterwarnings("ignore")

# stderr 로그 억제
@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

def split_sections(text):
    lines = text.split('\n')
    extracted_data = []
    current_chapter = None
    current_section = None
    current_content = []

    def flush_content():
        if current_content:
            extracted_data.append({
                "chapter": current_chapter,
                "section": current_section,
                "content": " ".join(current_content).strip()
            })
            current_content.clear()

    def preprocess_line(line):
        line = re.sub(r"(제\s*\d+\s*장)", r"\n\1", line)
        line = re.sub(r"(제\s*\d+\s*조\s*\()", r"\n\1", line)
        return [l.strip() for l in line.split('\n') if l.strip()]

    for line in lines:
        for subline in preprocess_line(line):
            if not subline or re.match(r"^-\s*\d+\s*-$", subline):
                continue

            chapter_match = re.match(r"(제\s*\d+\s*장)", subline)
            section_match = re.search(r"(제\s*\d+\s*절\s*[가-힣\s]+)", subline)
            article_match = re.match(r"(제\s*\d+\s*조\s*\()", subline)

            if chapter_match:
                flush_content()
                current_chapter = chapter_match.group(1)
                current_section = None
                rest = subline.replace(current_chapter, "").strip()
                if rest:
                    current_content.append(f"{current_chapter} {rest}".strip())
                continue

            elif section_match:
                flush_content()
                current_section = section_match.group(1)
                rest = subline.replace(current_section, "").strip()
                if rest:
                    current_content.append(rest)
                continue

            elif article_match:
                flush_content()
                current_content.append(subline)
                continue

            else:
                current_content.append(subline)

    flush_content()
    return extracted_data

def extract_text_and_tables(pdf_path, output_path):
    start_time = time.time()  # ⏱️ 시작 시간 기록

    with suppress_stderr():
        pdf = pdfium.PdfDocument(pdf_path)
    n_pages = len(pdf)
    all_entries = []

    headline = os.path.splitext(os.path.basename(pdf_path))[0]
    current_chapter = ""
    current_section = ""
    last_chapter_logged = ""
    last_section_logged = ""

    for page_num in range(n_pages):
        page = pdf[page_num]
        textpage = page.get_textpage()
        text = textpage.get_text_bounded().strip()

        if text:
            lines = text.split('\n')
            if lines:
                first_line = lines[0].strip()

                # 대괄호 포함한 코드 매칭 허용
                code_match = re.match(r"\[?(\d{1,2}-\d{1,2}-\d{1,2})\]?\s+(.+)", headline.strip())
                if code_match:
                    code_part = code_match.group(1)  # "2-1-1"
                    name_part = code_match.group(2)  # "한성대학교 학칙"

                    patterns_to_remove = [
                        headline.strip(),                         # "[2-1-1] 한성대학교 학칙"
                        f"{name_part} [{code_part}]",             # "한성대학교 학칙 [2-1-1]"
                        f"[{code_part}] {name_part}",             # "[2-1-1] 한성대학교 학칙"
                        f"{code_part} {name_part}",               # "2-1-1 한성대학교 학칙"
                        f"{name_part} {code_part}",               # "한성대학교 학칙 2-1-1"
                    ]

                    for pattern in patterns_to_remove:
                        if pattern in first_line:
                            lines[0] = first_line.replace(pattern, "").strip()
                            break

            text = '\n'.join(lines).strip()

        if text:
            sections = split_sections(text)
            for sec in sections:
                is_new_article = bool(re.match(r"제\s*\d+\s*조", sec['content']))

                if sec.get("chapter"):
                    current_chapter = sec["chapter"]
                    current_section = ""
                    if current_chapter != last_chapter_logged:
                        last_chapter_logged = current_chapter

                if sec.get("section"):
                    current_section = sec["section"]
                    if current_section != last_section_logged:
                        all_entries.append(
                            f"page: {page_num + 1}\nheadline: {headline}\ncontent: {current_chapter} {current_section}\n\n"
                        )
                        last_section_logged = current_section

                if is_new_article:
                    prefix = current_chapter
                    if current_section:
                        prefix += f" {current_section}"
                    entry = f"page: {page_num + 1}\nheadline: {headline}\ncontent: {prefix} {sec['content'].strip()}\n\n"
                else:
                    # 이전 조의 연속 내용
                    entry = f"page: {page_num + 1}\nheadline: {headline}\ncontent: {sec['content'].strip()}\n\n"

                all_entries.append(entry)

        try:
            with suppress_stderr():
                tables = camelot.read_pdf(pdf_path, pages=str(page_num + 1))
                for table in tables:
                    df = table.df
                    try:
                        md_table = df.to_markdown(index=False)
                    except AttributeError:
                        md_table = tabulate(df.values.tolist(), headers=df.iloc[0].tolist(), tablefmt="pipe")

                    entry = f"page: {page_num + 1}\nheadline: {headline}\ncontent:\n{md_table}\n\n"
                    all_entries.append(entry)
        except Exception as e:
            print(f"[표 추출 오류] 페이지 {page_num + 1}: {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(all_entries)

    end_time = time.time() 
    elapsed_time = end_time - start_time
    print(f"✅ 저장 완료: {output_path}")
    print(f"⏱️ 처리 시간: {elapsed_time:.2f}초")

    #return elapsed_time  # ⏱️ 시간 반환

# def process_single_file(file_path):
#     base_name = os.path.splitext(os.path.basename(file_path))[0]
#     output_path = os.path.join('./학칙txt', f"{base_name}.txt")
#     elapsed = extract_text_and_tables(file_path, output_path)
#     return (base_name, elapsed)

# def main():
#     input_dir = './학칙pdf'
#     output_dir = './학칙txt'
#     os.makedirs(output_dir, exist_ok=True)

#     file_paths = glob.glob(os.path.join(input_dir, '*.pdf'))

#     timing_results = []  # ⏱️ 파일별 처리 시간 저장

#     with Pool(processes=cpu_count()) as pool:
#         timing_results = pool.map(process_single_file, file_paths)

#     # ⏱️ 타이밍 정보 파일로 저장 (CSV 형식)
#     with open("timetochage.csv", "w", newline="", encoding="utf-8") as f:
#         writer = csv.writer(f)
#         writer.writerow(["파일명", "처리시간(초)"])
#         writer.writerows(timing_results)

#     print("📘 모든 PDF 처리 완료!")

# if __name__ == "__main__":
#     main()