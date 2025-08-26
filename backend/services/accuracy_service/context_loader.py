import pandas as pd

def read_csv_as_text_list(file_path: str) -> list[str]:
    """
    CSV 파일을 읽어서 각 행을 문자열로 합친 리스트로 반환하는 함수
    - 각 행은 ' | '로 구분해서 하나의 문자열로 변환
    - 실패 시 빈 리스트 반환
    """
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        lines = df.astype(str).apply(lambda row: ' | '.join(row), axis=1).tolist()
        return lines
    except Exception as e:
        print(f"CSV 읽기 오류 ({file_path}): {e}")
        return []