import pandas as pd

def read_csv_as_text_list(file_path: str) -> list[str]:
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        lines = df.astype(str).apply(lambda row: ' | '.join(row), axis=1).tolist()
        return lines
    except Exception as e:
        print(f"CSV 읽기 오류 ({file_path}): {e}")
        return []