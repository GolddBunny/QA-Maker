import subprocess

def convert_docx_file(file_path, output_path, original_filename):
    """
    주어진 DOCX 파일에서 텍스트를 추출합니다.
    """
    try:
        subprocess.run([
            'pandoc',
            '-f', 'docx',
            '-t', 'markdown',
            file_path,
            '-o', output_path
        ], check=True)
        print(f"[pandoc] 변환 완료: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"[pandoc] 변환 실패: {e}")
