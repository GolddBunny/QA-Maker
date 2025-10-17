## 🖥️ 프로젝트 테스트 방법
---
### 1. 관리자 테스트 방법<br><br>
<img width="2099" height="1581" alt="관리자테스트방법" src="https://github.com/user-attachments/assets/7d63ca6c-69c4-4158-bb7a-138e27b2ebaf" /><br><br>

### 2. 사용자 테스트 방법<br><br>
<img width="1738" height="1771" alt="사용자테스트방법" src="https://github.com/user-attachments/assets/ed35b8c1-86f2-4b03-8b6f-2a2ba2ac938f" /><br><br>
---
# 프로젝트 설치 및 실행 가이드

## 체크리스트

- [ ] 가상 환경 생성 및 활성화
- [ ] requirements.txt 의존성 설치
- [ ] .env 파일 설정
- [ ] Firebase 서비스 계정 JSON 파일 넣기
- [ ] backend/firebase_config.py 에서 Fireabse JSON 파일명 수정
- [ ] `.env` 파일 넣기

---

## 환경 설정

1. 레포지토리 fork 한 후 clone
2. 새로운 가상환경 생성 및 활성화
  
  ```
  python -m venv qamaker
  
  # Windows
  qamaker\Scripts\activate
  
  # Mac/Linux
  source qamaker/bin/activate
  
  ```
3. 의존성 설치

  ```
  cd backend
  pip install -r requirements.txt
  
  cd ../frontend
  npm install
  ```

---
# API 키 및 설정 파일 

## 1. OpenAI API 키

다음 위치에 .env 파일을 만들고 키를 설정:

- `data/{모든 폴더}/.env`:
    ```
    GRAPHRAG_API_KEY=sk-your-openai-api-key-here
    ```
- `backend/accuracy_service/.env`:
    ```
    GRAPHRAG_API_KEY=sk-your-openai-api-key-here
    ```

## 2. Firebase 설정

- `frontend/src/.env`  
  Firebase 설정을 여기에 입력 (실제 값으로 교체):
    ```
    REACT_APP_FIREBASE_API_KEY=your-api-key
    REACT_APP_FIREBASE_AUTH_DOMAIN=your-app.firebaseapp.com
    REACT_APP_FIREBASE_PROJECT_ID=your-project-id
    REACT_APP_FIREBASE_STORAGE_BUCKET=your-app.appspot.com
    REACT_APP_FIREBASE_MESSAGING_SENDER_ID=xxxx
    REACT_APP_FIREBASE_APP_ID=xxxx
    REACT_APP_FIREBASE_MEASUREMENT_ID=G-xxxx
    ```

- `backend/services/firebase/`  
&nbsp;&nbsp;Firebase 서비스 계정 키 파일 (key.json)을 이 디렉토리에 배치
&nbsp;&nbsp;**backend/services/firebase/config.py에서 JSON 키 파일명과 동일하게 설정해야 함.**

---

## 3. 입력 데이터 설정 
- `output` 폴더(SNU CSE, 한성대, 회사 페이지 등)를 `data/input` 아래에 배치 (이미 되어 있음)
  Example:
    ```
    /data/input/{snu_cse_page_id}/output
    /data/input/{hansung_uni_page_id}/output
    /data/input/{company_page_id}/output
    ```
    
- 각 `data/input/{page_id}` 폴더에는 OpenAI API 키가 포함된 .env 파일이 필요:
    ```
    GRAPHRAG_API_KEY=sk-your-openai-api-key-here
    ```
    Example:
    ```
    data/input/{snu_cse_page_id}/.env
    ```

  ---

## 실행
### Backend
  
  ```
  cd backend
  python app.py
  ```

### Frontend
  
  ```
  cd frontend
  npm start
  ```

---

## 주의 사항

- OpenAI API 키와 Firebase 설정 없이는 프로젝트 실행 불가
- API 키나 JSON 파일을 공유하지 말고 로컬에만 보관

---

## 흔한 문제

- **프론트엔드가 빈 화면으로 표시될 때**  
&nbsp;&nbsp;Firebase 설정 오류일 가능성이 높음. .env 파일 확인 후 앱 재시작.

- **"응답을 받지 못했습니다" 라는 응답을 받았을 때**  
&nbsp;&nbsp;OpenAI API 키 문제일 가능성. .env의 키 값을 확인.

- **입력 데이터가 인식되지 않을 때**  
&nbsp;&nbsp;output 폴더가 data/input/{page_id} 아래에 있는지, 각 폴더에 .env 파일이 있는지 확인.

---

## 외부 서비스 설정

### 1. OpenAI API 키 - GPT 모델 사용을 위한 유료 API키 필요
1) https://openai.com/ko-KR/index/openai-api/ 주소로 이동하여 로그인한다. 
2) API platform에 들어간다. (https://platform.openai.com/docs/overview)
3) Settings에서 API keys 항목에 들어간다. (https://platform.openai.com/settings/organization/api-keys)
4) 우측 위 Create new secret key를 눌러 api key를 발급한다.
5) Billing 항목에 들어가 Add to credit balance를 눌러 돈을 충전한다. (5$부터 충전가능함) 
(https://platform.openai.com/settings/organization/billing/overview)
6) 만든 키를 project의 다음 위치에 넣어준다: <br>

```
data/{모든 폴더}/.env 
backend/accuracy_service/.env
```

.env 파일의 내용은 다음과 같다: <br>
`GRAPHRAG_API_KEY=sk-your-openai-api-key-here`

### 2. Firebase : Database, Storage 사용
1) https://console.firebase.google.com/?hl=ko 주소로 이동하여 로그인한다.
2) 새 Firebase 프로젝트 만들기를 누른다.
3) 프로젝트 이름에 QA Maker 를 입력하고 계속 버튼을 눌러 프로젝트 만들기 버튼을 누른다.
4) 프로젝트 생성이 되면 ‘+앱 추가’ 버튼을 눌러 웹 버튼을 누른다.
5) 웹 앱에 Firebase 추가 화면이 나온다.
6) 앱 닉네임에 QA Maker를 작성하고 앱 등록 버튼을 누른다.
7) Firebase SDK 추가에서 npm 사용 화면에 나온 코드를 확인한 후 const firebaseConfig 아래에 나온 apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId, measurementId의 값들을 project의 다음 위치에 아래 형식과 같이 넣어준다: <br>
`frontend/src/.env`
	```
	REACT_APP_FIREBASE_API_KEY=your-api-key
	REACT_APP_FIREBASE_AUTH_DOMAIN=your-app.firebaseapp.com
	REACT_APP_FIREBASE_PROJECT_ID=your-project-id
	REACT_APP_FIREBASE_STORAGE_BUCKET=your-app.appspot.com
	REACT_APP_FIREBASE_MESSAGING_SENDER_ID=xxxx
	REACT_APP_FIREBASE_APP_ID=xxxx
	REACT_APP_FIREBASE_MEASUREMENT_ID=G-xxxx
	```
8) 콘솔로 이동 버튼을 누른다.
9) 프로젝트 개요 옆 프로젝트 설정 버튼을 누른다. 
10) 서비스 계정 항목에 들어간다.
11) 아래 ‘새 비공개 키 생성’ 버튼을 눌러 json 파일을 다운받는다.
12) 다운받은 json 파일을 다음 위치에 넣어준다: <br>
`backend/services/firebase/`
13) `backend/firebase_config.py`파일의 8번째 줄의 `qamaker-e32d7-firebase-adminsdk-fbsvc-9c8756c5bc.json` 위치에 다운받은 json 파일 이름으로 변경해준다.

