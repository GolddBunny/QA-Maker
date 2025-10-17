# Project Installation and Execution Guide

## Checklist

- [ ] Create and activate a virtual environment
- [ ] Install dependencies from requirements.txt
- [ ] Configure .env file
- [ ] Place Firebase service account JSON file
- [ ] Update backend/firebase_config.py with the Firebase JSON file name
- [ ] Place `.env` files in appropriate folders

---

## Environment Setup

1. Fork the repository and clone it
2. Create a new virtual environment and activate it
  
  ```
  python -m venv qamaker
  
  # Windows
  qamaker\Scripts\activate
  
  # Mac/Linux
  source qamaker/bin/activate
  
  ```
3. Install dependencies

  ```
  cd backend
  pip install -r requirements.txt
  
  cd ../frontend
  npm install
  ```

---
# API Keys and Configuration Files

## 1. OpenAI API Key

Create .env files at the following locations and set your API key:

- `data/{all folders}/.env`:
    ```
    GRAPHRAG_API_KEY=sk-your-openai-api-key-here
    ```
- `backend/accuracy_service/.env`:
    ```
    GRAPHRAG_API_KEY=sk-your-openai-api-key-here
    ```

## 2. Firebase Setup

- `frontend/src/.env`  
&nbsp;&nbsp;Enter your Firebase configuration here (replace with actual values):
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
&nbsp;&nbsp;Place the Firebase service account key file (key.json) in this directory.
&nbsp;&nbsp;Make sure backend/services/firebase/config.py uses the same JSON file name.

---

## 3. Input Data Setup
- Place the `output` folders (e.g., SNU CSE, Hansung Univ., company pages) under `data/input` (already done)
  Example:
    ```
    /data/input/{snu_cse_page_id}/output
    /data/input/{hansung_uni_page_id}/output
    /data/input/{company_page_id}/output
    ```
    
- Each data/input/{page_id} folder must contain a .env file with your OpenAI API key:
    ```
    GRAPHRAG_API_KEY=sk-your-openai-api-key-here
    ```
    Example:
    ```
    data/input/{snu_cse_page_id}/.env
    ```

  ---

## Execution
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

## Notes
- The project will not run without the OpenAI API key and Firebase configuration
- Do not share API keys or JSON files; keep them local

---

## Common Issues

- **Frontend shows a blank page**  
&nbsp;&nbsp;This usually indicates a Firebase configuration error. Check the .env file and restart the app.

- **"Failed to get a response” error**  
&nbsp;&nbsp;This usually indicates an OpenAI API key issue. Verify the .env key values.

- **Input data not recognized**  
&nbsp;&nbsp;Ensure output folders are under data/input/{page_id} and that each folder contains a .env file.
