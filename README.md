# QA Maker
도메인에 특화된 Q&A 시스템을 자동 생성하는 웹 프레임워크<br>

---

## 작업기간
2025.03.01~2025.05.30<br>

---

## 목표
1. 기존의 도메인 내 검색이 잘 되지 않는 문제와 새로운 검색 엔진을 구축할 때의 비용과 시간 문제 해결
2. 자연어 질의응답과 추론이 가능한 Q&A 시스템<br>

---

## 전체 시스템 구조
![image](https://github.com/user-attachments/assets/f6133e37-d427-431e-b3bf-6329c0d8df0c)<br><br>


| 구분                    | 역할                                         | 주요 모듈                                                                 |
|-----------------------|--------------------------------------------|--------------------------------------------------------------------------|
| **Admin Page**        | 도메인별 Q&A 시스템 구축 및 관리               | - URL / 문서 업로드 (유효성 검사 포함)  <br> - 그래프 시각화 (지식 그래프 제공)       |
| **QA Gen 서버**        | Q&A 시스템 자동 생성 및 그래프 구축             | - 도메인 정보 관리  <br> - URL 크롤링 / 문서 수집  <br> - HTML / 문서 구조화  <br> - 지식 그래프 생성 (GraphRAG, LanceDB 저장) |
| **검색 Page**         | 사용자 질의에 신뢰도 높은 Q&A 제공              | - 질의응답 (근거 문서, 관련 질문 포함)  <br> - 그래프 시각화 (엔티티 관계 표시)       |
| **도메인 Q&A System** | 실제 Q&A 서비스 제공                         | - 답변 생성 (GraphRAG + OpenAI LLM)  <br> - 질문 수집 / 분석 (패턴 및 만족도 분석)   |<br><br>

---

## Q&A 시스템 생성 과정
![image](https://github.com/user-attachments/assets/da768450-0142-428e-bc84-c3c9b4013e39)<br><br>

---

## 시스템 동작 사진

### 1. 시스템 생성 시 홈 화면
![image](https://github.com/user-attachments/assets/f8e8c465-8db0-4ddd-8a3b-1a187ad7e149)<br>

### 2. Q&A 시스템 생성 화면
![image](https://github.com/user-attachments/assets/878963ed-800f-483c-a4a4-9f162f107c4b)<br>

### 3. Q&A 시스템 구축 화면
![image](https://github.com/user-attachments/assets/8d03e119-7594-40af-b950-a3434cfeecd4)<br>

### 4. 생성된 Q&A 시스템 데이터 확인 화면 (Log Analyzer)
![image](https://github.com/user-attachments/assets/ad4701de-88a5-41b8-8750-a4e3ab78f04d)<br>

### 5. 생성된 Q&A 시스템의 홈 화면
![image](https://github.com/user-attachments/assets/a5417fd9-70a2-4345-94fd-be202f14790f)<br>

### 6. Q&A 시스템의 질의응답 채팅화면
![image](https://github.com/user-attachments/assets/11220155-9a0f-49a5-9c36-102c366952f2)<br>

### 7. Q&A 시스템의 근거 문서 시각화 채팅화면
![image](https://github.com/user-attachments/assets/397ee53e-c99d-4262-af53-aa9259bf8e3e)<br>

### 8. Q&A 시스템의 응답 지식 그래프 시각화 채팅화면
![image](https://github.com/user-attachments/assets/3dde01df-896c-45c1-85ac-a369f77ae99d)<br>

---

## 기대효과
1. 어떤 도메인이든 URL만으로 도메인에 특화된 Q&A 시스템 즉시 생성
2. 공개 도메인 뿐 아니라 기업 내부 비공개 도메인에도 적용 가능
3. 짧으면 30분, 길면 1일 이내 Q&A 시스템 자동 구축으로 개발 시간 및 비용 대폭 절감
4. 대학, 중소 기업 등 다양한 기관에 즉시 판매 가능한 높은 상업적 가치
5. 독보적인 기술력을 특허로 출원하여 지적 재산권 확보 가능

