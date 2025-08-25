# QA Maker
> 도메인에 특화된 Q&A 시스템을 자동으로 생성하는 웹 프레임워크<br>

---

## 📝 작품 소개
### 1. 개발 배경
  오늘날 정보 검색은 우리 일상의 필수 요소가 되었으며, 검색 시스템은 사용자가 원하는 정보를 빠르고 정확하게 찾아주는 핵심 도구로 자리잡았다. 현재 검색 시스템은 구글, 네이버 같은 대규모 인터넷 검색 엔진과 대학·기업 등의 특정 도메인 검색 시스템으로 구분된다. 대규모 검색 엔진은 LLM을 활용한 자연어 처리와 AI 기반 추론 기술로 맥락을 파악한 답변을 제공하는 반면, 특정 도메인 검색 시스템은 여전히 키워드 매칭 방식에 의존하고 있어 심각한 한계를 보이고 있다.

특정 도메인 검색 시스템의 주요 문제점은 다음과 같다:

- 키워드 불일치 시 검색 결과 부재 또는 무관한 결과 대량 출력
- 자연어 질의 처리 불가능
- 맥락과 의미를 고려한 추론 기능 부재
- 반복적인 키워드 조합 입력의 번거로움

또한 도메인 내 검색 시스템 개발에는 현실적 제약이 존재한다:

- 웹사이트 전체 재개발 또는 고가 검색 엔진 구축 필요
- LLM 기반 AI 시스템 도입 시 천문학적 비용 발생
- 지속적인 막대한 유지보수 및 운영 비용
- 전문 인력 확보의 어려움과 장기간 개발 시간 소요

### 2. 개발 목적 및 목표
> 도메인 내 검색 시스템의 구조적 한계와 새로운 검색 시스템 구축의 현실적 제약을 동시에 해결하기 위해, 특정 도메인의 URL만 입력하면 자연어 질의응답과 추론이 가능한 Q&A 시스템을 자동으로 생성하는 QA Maker를 개발한다.

#### - 핵심 개발 목표 -
1. **완전 자동화된 Q&A 시스템 생성**: 도메인 URL 하나만 입력하면 전체 웹사이트의 모든 하위 페이지와 첨부파일까지 자동 수집하여 즉시 Q&A 시스템 생성
2. **다양한 문서 형식 지원 및 확장**: 웹 페이지뿐만 아니라 PDF, HWP, DOCX, TXT 등 다양한 형식의 문서를 지식그래프에 통합하여 시스템의 지속적 확장 가능
3. **GraphRAG 기반 대규모 지식그래프 구축**: 수집된 데이터에서 엔티티와 관계를 추출하여 정보 간 연결성을 확보하고 종합적 추론 기능 제공
4. **구조화되지 않은 데이터의 지식그래프 구조화**: HTML, PDF, HWP 등 구조화되지 않은 데이터를 LLM이 정확한 지식그래프로 추출할 수 있도록 전처리 및 구조화
5. **Flask 기반 웹 서비스 제공**: 웹 브라우저를 통한 언제든지 접근 가능하며, 추가 설치나 복잡한 설정 없이 쉽게 이용할 수 있는 웹 애플리케이션 구현

### 3. 작품 개요
  QA Maker는 사용자가 특정 도메인의 URL을 입력하면, 해당 웹사이트를 크롤링하고 수집된 데이터를 구조화하여 지식 그래프를 자동으로 생성한다. 이후 이 지식 그래프를 기반으로 사용자가 질의응답할 수 있는 Q&A 시스템이 구축되며, 추가적으로 구축된 지식 그래프의 세부 정보를 확인할 수 있는 Log Analyzer가 생성된다. 
<br><br>

<img width="2971" height="1740" alt="Group 706 (2)" src="https://github.com/user-attachments/assets/a6063209-cee3-408a-9ed0-9e53b0a50892" /> <br><br>

**- QA Maker의 주요기능 -**
-	QA Maker의 주요 기능
    +  웹 크롤링
    +  구조화
    +  지식 그래프 생성
    +  QA Maker 실행 후 생성 결과물

-	Q&A 시스템의 주요 기능
    +  질의응답
    +  근거 URL 및 문서 시각화 
    +  정확도
    +  사용자 만족도
    +  관련 질문 추천

---
## 시스템 구성 및 아키텍처
### 1. QA Maker 시스템 전체 구성
<br>
    QA Maker 시스템은 도메인 URL만으로 해당 도메인의 질의응답 시스템을 자동으로 생성하는 웹 프레임워크이다. QA Maker 시스템은 그림 9과 같이 크게 Q&A 생성 서버 부분과 생성된 Q&A 시스템으로 구성된다. 
  Q&A 생성 서버는 React 기반 관리자 페이지와 Flask 기반 Q&A 생성 서버로 구성된다. 생성된 Q&A 시스템은 React 기반 사용자 페이지와 Flask 기반 도메인 Q&A 시스템으로 구성된다.  
  Q&A 시스템을 만들고자 하는 관리자는 웹 브라우저에서 Q&A 생성 서버의 URL에 접속하여 Q&A 생성 서버를 활용한다. 도메인 URL 이나 문서를 등록하면 자동으로 지식 그래프를 생성하고 Q&A 생성 서버와 독립적으로 운영되는 Q&A 시스템이 생성된다. 
  질의하고자 하는 사용자는 웹 브라우저에서 생성된 Q&A 시스템의 URL에 접속하여 Q&A 시스템의 사용자 페이지를 통해 질의응답할 수 있다. 
<br><br>
<img width="1384" height="812" alt="깃허브 작품개요ㅗ" src="https://github.com/user-attachments/assets/aca8b153-ac08-4ba1-87a3-221b7d54d5ee" />

### 2. Q&A 생성 서버

<details>
  <summary><h4>1) 관리자 페이지</h4></summary>
     <details>
      <summary>새 도메인 생성 모듈</summary>
        새 도메인 생성 모듈을 통해 관리자가 새로운 도메인을 추가할 수 있다.
     </details> 
     <details>
      <summary>URL / 문서 업로드 모듈</summary>
        관리자가 도메인 URL이나 PDF, HWP, DOCX 등의 문서를 업로드할 수 있으며, 입력된 URL과 문서의 유효성을 자동으로 검증한다.
     </details> 
     <details>
      <summary>로그 분석 모듈</summary>
        시스템 생성이 완료되면 로그 분석 페이지가 생성되어 크롤링 시간, 구조화 시간, 지식 그래프 생성 시간 등 단계별 처리 기록을 제공한다. 로그 분석 모듈을 통해 수집된 문서와 URL 목록을 확인하고 D3.js 기반으로 생성된 지식 그래프를 시각적으로 탐색할 수 있으며, 줌과 세부 정보 표시 등의 탐색 기능을 제공한다.
     </details> 
</details> 
<details>
  <summary><h4>2) Q&A 생성 서버</h4></summary>
     <details>
      <summary>도메인 정보 관리 모듈</summary>
        관리자가 웹 브라우저에서 새 도메인을 등록하면 Flask 내의 도메인 정보 관리 모듈이 해당 요청을 처리한다. 
     </details> 
     <details>
      <summary>URL 크롤링 및 문서 수집 모듈</summary>
        requests 라이브러리로 정적 HTML을 수집하고, JavaScript 기반 동적 페이지는 Selenium WebDriver로 처리한다. BeautifulSoup4를 통해 HTML을 파싱하여 관리자가 입력한 도메인 URL 내 모든 하위 페이지를 탐색하고, 업로드된 문서를 함께 수집한다.
     </details> 
     <details>
      <summary>HTML 및 문서 구조화 모듈</summary>
        JinaAPI를 활용한 웹페이지 마크다운 변환, pymupdf4llm을 통한 PDF 텍스트 추출, olefile과 zlib을 이용한 HWP 파일 처리, docx2pdf를 통한 DOCX 변환 등 각 문서 형식별 전용 라이브러리를 사용해 텍스트를 추출하고, 계층적 마크다운 형식으로 변환하여 저장한다.
     </details> 
     <details>
      <summary>지식 그래프 생성 모듈</summary>
        GraphRAG와 OpenAI LLM을 활용해 엔티티와 관계 정보를 추출하며, LanceDB에 entity-description 쌍으로 저장하고 Firebase DB를 통해 전체 지식 그래프를 관리한다.
     </details> 
</details>
<details>
  <summary><h4>3) lanceDB</h4></summary>
</details>
<details>
  <summary><h4>4) Firebase DB</h4></summary>
     <details>
      <summary>도메인 정보</summary>
        관리자가 등록한 도메인을 관리하며 도메인 추가 및 목록 조회 시 활용된다.
     </details> 
     <details>
      <summary>원본 문서</summary>
        크롤링된 URL 및 기타 문서 원본을 저장하여 응답 시 근거 자료로 활용된다.
     </details> 
     <details>
      <summary>질문 이력</summary>
       사용자 질의와 생생된 응답, 만족도 평가를 기록한다.
     </details> 
     <details>
      <summary>지식그래프 데이터</summary>
       Q&A 시스템 생성이 완료된 후 해당 도메인의 지식그래프 전체를 저장한다
     </details> 
</details>

### 3. 생성된 Q&A 시스템

<details>
  <summary><h4>1) 사용자 페이지</h4></summary>
     <details>
      <summary>질의응답 모듈</summary>
        사용자가 입력한 자연어 질의를 GraphRAG에 전달하여 OpenAI API를 활용해 생성된 응답과 함께 근거 문서, 정확도, 관련 질문을 함께 화면에 표시한다.
     </details> 
     <details>
      <summary>그래프 시각화 모듈</summary>
        응답 생성 시 참고된 엔티티와 관계를 D3.js를 사용해 지식 그래프로 시각화하여 답변의 근거를 명확히 보여준다.
     </details> 
</details> 
<details>
  <summary><h4>2) 생성된 Q&A 시스템</h4></summary>
      <details>
        <summary>답변 생성 모듈</summary>
          사용자가 입력한 질의를 GraphRAG를 통해 관련 엔티티와 관계를 조회하고, OpenAI API를 활용해 자연스러운 답변을 생성하여 반환한다. 답변과 함께 근거 문서가 필요한 경우 PyMuPDDF 라이브러리와 LibreOffice 소프트웨어를 사용하며, 지식 그래프를 시각화하는 경우 Firebase DB를 통해 지식 그래프 정보를 조회한다
       </details> 
       <details>
        <summary>질의 수집 및 분석 모듈</summary>
          Firebase를 활용하여 사용자 질의 및 만족도를 수집하고 이를 해당 도메인 정보 품질의 지표로 활용한다.
     </details> 
</details> 

---
## 기대 효과
- **홈페이지를 가진 모든 도메인에 활용 가능** <br>
  공개된 웹 사이트는 물론, 기업 내부 인트라넷이나 로컬 문서에도 동일하게 적용할 수 있다. 외부에 공개할 수 없는 민감한 데이터도 안전하게 처리하며, 내부 전용 Q&A 시스템을 손쉽게 구축할 수 있다.

- **Q&A 시스템 자동 구축으로 개발 시간 및 비용 대폭 절감** <br>
  기존처럼 별도의 모델 설계나 데이터 전처리, 수작업 튜닝 과정 없이도 30분 ~ 2일 내에 Q&A 시스템 구축이 완료되어, 인력과 개발 기간, 비용을 대폭 절감할 수 있다.

- **URL 입력만으로 도메인 특화 Q&A 시스템 즉시 생성** <br>
  사용자가 단순히 URL을 입력하거나 문서 업로드만 하면 자동으로 내용을 분석해 도메인에 특화된 Q&A 시스템을 빠르게 구축할 수 있어, 별도의 특별한 기술이나 전문 지식 없이 누구나 쉽게 구축할 수 있다.

- **공개 소프트웨어의 사회적 가치 창출** <br>
  교육기관, 연구소, 공공 기관 등에서도 전문 개발팀 없이 Q&A 시스템을 직접 구축할 수 있으므로, 상업적 목적을 넘어 공공적·사회적 가치도 실현된다. 

- **공개 소프트웨어 생태계 확장 및 기여** <br>
  QA Maker는 GNU 라이선스로 공개 배포하여 다른 개발자들이 자유롭게 개선하고 확장할 수 있도록 한다. 특히 공개 소프트웨어들을 창의적으로 조합한 새로운 접근 방식을 제시함으로써, 향후 프로젝트들이 더욱 발전된 형태로 등장할 수 있는 기반을 마련한다.

---
## 활용 방안
- **모든 도메인 웹사이트 대해 검색 시스템 자동 생성** <br>
  연구소, 학회, 기업 등 모든 도메인 웹사이트에 대해 URL만 입력하면, 해당 도메인에 특화된 Q&A 시스템을 자동으로 구축할 수 있다.

- **기관 내부의 지식 관리 시스템** <br>
  기업의 매뉴얼, 정책 문서, 기술 문서 등을 기반으로 자동화된 Q&A 시스템을 구축하여 직원들이 필요한 정보를 신속하게 검색할 수 있다. 신규 입사자 교육이나 사내 지식 검색에 활용 가능한 시스템을 빠르게 구축할 수 있다.

- **게시판 검색에 활용** <br>
온라인 커뮤니티나 게시판의 기존 게시글, 댓글, FAQ 등을 시스템에 입력하여 반복적인 질문에 대한 자동 답변 시스템을 구축할 수 있다. 중복 질문을 줄이고 커뮤니티 운영자의 관리 부담을 경감시키며, 관련 게시글 링크를 제공하여 사용자가 더 깊이 있는 정보를 탐색할 수 있도록 지원한다.

- **이러닝 플랫폼에서 강의 노트 기반 Q&A 시스템 튜터 제공** <br>
  온라인 강의에 사용되는 교안 강의 노트 등을 바탕으로 학생이 질문하면 강의 맥락을 이해한 답변을 제공할 수 있다.

- **누구나 활용 가능한 웹 기반 지식 관리 도구** <br>
  별도의 기술적 지식 없이도 URL이나 문서를 업로드하고 간단한 설정만으로 도메인별 Q&A 시스템을 손쉽게 생성할 수 있다. 이는 대중적 접근성과 상업적 활용 가능성을 높인다.

---
## 프로젝트의 혁신성 및 차별성 
본 프로젝트는 단순한 키워드 검색의 한계를 극복하고, 최신 GraphRAG 기반 지식그래프 기술을 활용하여 자동화된 자연어 질의응답 시스템을 제공한다. 주요 혁신성 및 차별성은 다음과 같다.

**①	 URL 입력만으로 완전 자동화된 Q&A 시스템 생성** <br>
QA Maker는 사용자가 도메인 URL 하나만 입력하면 해다 도메인의 모든 웹 페이지와 첨부 문서를 자동으로 수집하고, 지식그래프를 생성하여 자연어 질의응답과 추론이 가능한 Q&A 시스템을 생성한다. 전 과정이 한 번의 입력으로 자동으로 진행되며, 추가 설정이나 전문 지식 없이도 즉시 사용 가능한 완전 자동화 시스템이다. 

**②	 GraphRAG 기반 지식 그래프 자동 생성**  <br>
최근 학술적으로 검증된 GraphRAG 기법을 활용하여 방대한 데이터를 구조화하고, 데이터 간의 관계를 반영한 지식그래프를 자동 생성한다. 이를 기반으로 사용자의 자연어 질의에 정확하고 맥락 있는 응답을 제공할 수 있다.

**③	 자연어 질의응답 및 추론 기능 지원**  <br>
기존 검색 시스템에서 어려웠던 자연어 질의응답과 추론 기능을 지원한다. GraphRAG로 질의에 관련된 정보를 찾고, OpenAI LLM을 활용해 자연스러운 완결성 있는 문장을 생성한다. 질의 유형에 따라 단순 응답과 추론 응답을 구분해 제공하여, 사실 기반 질의와 추론형 질의 모두에서 높은 품질을 유지한다.

**④	 투명한 응답 검증 및 품질 지표 제공**  <br>
사용자는 응답과 함께 근거 URL과 문서를 확인할 수 있다. 또한, 참조된 엔티티와 관계가 지식그래프로 시각화되어 응답의 생성 과정을 투명하게 검증할 수 있으며, 정확도 지표를 제공하여 응답 품질을 수치로 확인할 수 있다.

**⑤	 문서 계층 구조 보존을 통한 정확한 문맥 이해**  <br>
QA Maker는 문서 간의 연관관계와 문서 내부의 상하 관계를 그대로 반영해 계층 구조를 보존함으로써, 문서 구조와 문맥을 정확하게 이해할 수 있다. 

**⑥	 로그 분석 기능 제공**  <br>
관리자는 Log Analyzer에서 Q&A 시스템의 생성 과정의 세부 데이터를 확인할 수 있다. 지식 그래프를 생성하는 각 단계별 처리 시간과 생성된 노드와 엣지 수, 총 URL 및 문서 수, 시각화된 지식그래프까지 확인 가능하다. 이 기능을 통해 별도의 분석 도구 없이도 시스템 품질을 상시 점검하고 개선할 수 있다. 

**⑦	 자동화된 시스템으로 구축 시간 및 비용 절감** <br>
자체 개발한 크롤링 로직과 다양한 문서의 구조화, GraphRAG 기반 지식그래프 생성 엔진을 자동화하여 기존 수개월 이상 걸리던 도메인별 Q&A 시스템 구축 기간을 대폭 단축하였다. 또한 Flask와 React기반의 경량 구조로 구현하여 구축 및 운영 비용을 절감하고 유지보수와 확장이 용이하다. 

---
## ⚙️ 개발 환경

![MacOS](https://img.shields.io/badge/MacOS-AAAAAA?style=for-the-badge&logo=apple&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)

## ⚙️ 개발 언어

![Python](https://img.shields.io/badge/Python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=white)
![CSS](https://img.shields.io/badge/CSS-1572B6?style=for-the-badge&logo=css3&logoColor=white)

## ⚙️ 개발 도구 / 라이브러리

![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![BeautifulSoup4](https://img.shields.io/badge/BeautifulSoup4-4.13.3-orange?style=for-the-badge)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.25.5-red?style=for-the-badge)
![Olefile](https://img.shields.io/badge/Olefile-0.46-lightgrey?style=for-the-badge)
![GraphRAG](https://img.shields.io/badge/GraphRAG-2.1.0-lightblue?style=for-the-badge)
![D3.js](https://img.shields.io/badge/D3.js-orange?style=for-the-badge&logo=d3.js&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.0-black?style=for-the-badge&logo=flask&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.12.0-green?style=for-the-badge&logo=selenium&logoColor=white)
![LanceDB](https://img.shields.io/badge/LanceDB-0.17.0-purple?style=for-the-badge)
![Firebase](https://img.shields.io/badge/Firebase-6.8.0-yellow?style=for-the-badge&logo=firebase&logoColor=black)
![OpenAI API](https://img.shields.io/badge/OpenAI-API-blueviolet?style=for-the-badge)

---
## 프로젝트 결과
  아래는 QA Maker를 이용한 서울대학교 컴퓨터공학부 홈페이지를 테스트 케이스로 삼아 Q&A 시스템 생성 과정과 기능을 보여준다.

### 1. Q&A 시스템 구축 화면<br><br>
<img width="1152" height="1315" alt="깃허브구축화면" src="https://github.com/user-attachments/assets/f1fda201-579f-4163-b003-e8436c3ef5c8" /><br><br>


### 2. Log Analyzer 페이지<br><br>
<img width="1005" height="547" alt="image" src="https://github.com/user-attachments/assets/02b7d052-5b3d-4c40-a419-c053c6fd20d5" /><br><br>


### 3. 생성된 Q&A 시스템의 홈 화면<br><br>
<img width="1546" height="923" alt="깃허브3_생성된 시스템홈" src="https://github.com/user-attachments/assets/0205bef7-0c17-4197-9565-92419f5dbe3d" /><br><br>


### 4. Q&A 시스템의 질의응답 채팅화면<br><br>
<img width="426" height="292" alt="깃허브4질의응답" src="https://github.com/user-attachments/assets/1ab70c10-4472-4dbf-a949-7b79ab3ecc49" /><br><br>


### 5. Q&A 시스템의 근거 문서 시각화 채팅화면<br><br>
<img width="1384" height="730" alt="깃허브5근거문서" src="https://github.com/user-attachments/assets/620427c9-2967-4a81-bb0c-a421dd663da6" /><br><br>


### 6. Q&A 시스템의 응답 지식 그래프 시각화 채팅화면<br><br>
<img width="1384" height="727" alt="깃허브6 지식 그래프" src="https://github.com/user-attachments/assets/f416fbe4-bd1d-43a0-a748-30ae4e56905c" /><br><br>

---
## 프로젝트 테스트 방법
---

### 1. 관리자 테스트 방법<br><br>
<img width="2099" height="1581" alt="관리자테스트방법" src="https://github.com/user-attachments/assets/7d63ca6c-69c4-4158-bb7a-138e27b2ebaf" /><br><br>



### 2. 사용자 테스트 방법<br><br>
<img width="1738" height="1771" alt="사용자테스트방법" src="https://github.com/user-attachments/assets/ed35b8c1-86f2-4b03-8b6f-2a2ba2ac938f" /><br><br>

---
## 📒 참고 자료
Microsoft GraphRAG: https://github.com/microsoft/graphrag
