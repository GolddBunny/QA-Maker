# QA 시스템 백엔드

이 디렉토리는 QA 시스템의 Flask 백엔드를 포함하고 있습니다.

## 설치 방법

1. 가상 환경 생성 및 활성화:
```bash
python -m venv venv
source venv/bin/activate  # Unix/MacOS
# 또는
venv\Scripts\activate  # Windows
```

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

## 실행 방법

```bash
flask run
# 또는
python app.py
```

## 디렉토리 구조

- `app.py`: 메인 애플리케이션 파일
- `routes/`: API 라우트 모듈
- `services/`: 비즈니스 로직 서비스
  - `graph_service/`: 그래프 생성 및 관리
  - `query_service/`: 쿼리 처리
  - `document_service/`: 문서 처리
- `utils/`: 유틸리티 함수
- `venv/`: 가상 환경 