qa_system/
├── frontend/                    # React 프론트엔드
│   ├── public/                  # 정적 파일
│   │   └── page/                # 페이지별 업로드된 파일
│   ├── src/
│   │   ├── pages/               # 페이지 컴포넌트 (AdminPage, ChatPage 등)
│   │   ├── components/          # 재사용 가능한 컴포넌트
│   │   │   ├── charts/          # 그래프 관련 컴포넌트
│   │   │   ├── chat/            # 채팅 관련 컴포넌트
│   │   │   └── navigation/      # 내비게이션 관련 컴포넌트
│   │   ├── services/            # API 호출 및 데이터 처리
│   │   │   └── api.js           # 백엔드 API 통신 함수
│   │   ├── utils/               # 유틸리티 함수
│   │   │   └── storage.js       # 로컬 스토리지 관리 함수
│   │   ├── styles/              # CSS 및 스타일 파일
│   │   │   ├── ChatPage.css
│   │   │   └── Sidebar.css
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── package-lock.json
│
├── backend/                     # Flask 백엔드
│   ├── app.py                   # 메인 애플리케이션 파일
│   ├── routes/                  # API 라우트 모듈
│   │   ├── __init__.py
│   │   ├── document_routes.py   # 문서 관련 API 라우트
│   │   ├── page_routes.py       # 페이지 관련 API 라우트
│   │   └── query_routes.py      # 질의응답 관련 API 라우트
│   ├── services/                # 비즈니스 로직 서비스
│   │   ├── graph_service/       # 그래프 생성 및 관리
│   │   │   └── create_graph.py  # 그래프 생성 함수
│   │   ├── query_service/       # 쿼리 처리
│   │   └── document_service/    # 문서 처리
│   │       └── convert2txt.py   # 다양한 문서 형식을 텍스트로 변환
│   ├── utils/                   # 유틸리티 함수
│   ├── requirements.txt         # 파이썬 의존성
│   ├── .venv/                   # 가상환경
│   ├── __init__.py              # 패키지 초기화 파일
│   └── README.md                # 백엔드 설정 및 실행 방법
│
├── shared/                      # 프론트엔드와 백엔드 간 공유 자원
│   ├── models/                  # 데이터 모델 정의
│   └── config/                  # 공통 설정
│
├── data/                        # 실제 파일(PDF, 텍스트 문서, 파싱된 결과 등); DB에는 구조화된 데이터(메타데이터, 질문-답변 기록 등) 
│   ├── input/                   # 입력 문서 (페이지별 구분)
│   ├── processed/               # 처리된 문서
│   ├── graphs/                  # 생성된 그래프
│   └── parquet/                 # Parquet 파일
│       ├── output/              # 기본 출력 데이터
│       │   └── lancedb/         # LanceDB 데이터
│       └── update_output/       # 업데이트된 출력 데이터
│
├── docs/                        # 프로젝트 문서 (API 문서, 개발 및 사용자 가이드, 아키텍처 문서 등)
│   └── folder.md                # 프로젝트 폴더 구조 문서
│
├── .github/                     # GitHub 관련 
│   └── PULL_REQUEST_TEMPLATE.md # PR 템플릿 만들면 좋을,, 그런,, ㅎ,,
│
├── .gitignore
├── README.md                    # 프로젝트 개요 및 설정 방법
└── CONTRIBUTING.md              # 기여 가이드라인