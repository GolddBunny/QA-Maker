# Project Installation and Execution Guide

## Checklist

- [ ] Create and activate a virtual environment
- [ ] Install backend dependencies
- [ ] Install frontend dependencies
- [ ] Configure `.env` files
- [ ] Place Firebase service account JSON
- [ ] Update `config.py` to match Firebase JSON file name
- [ ] Place `output` folders under `data/input`    
- [ ] Create `.env` in each `data/input/{page_id}` folder  

---

## Environment Setup

1. Fork the repository and clone your fork
2. Create a new virtual environment and activate it
  
  ```
  python -m venv qamaker
  
  # Windows
  qamaker\Scripts\activate
  
  # Mac/Linux
  source qamaker/bin/activate
  
  ```
3. Install the dependencies

  ```
  cd backend
  pip install -r requirements.txt
  
  cd ../frontend
  npm install
  ```

---
# API Key and Configuration Files

## 1. OpenAI API Key

Create a `.env` file in the following locations and set your key:

- `data/parquet/.env`:
    ```
    GRAPHRAG_API_KEY=sk-your-openai-api-key-here
    ```
- `backend/accuracy_service/.env`:
    ```
    GRAPHRAG_API_KEY=sk-your-openai-api-key-here
    ```

## 2. Firebase Setup

- `frontend/src/.env`  
  Set your Firebase configuration here (replace with actual values):
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
  Place the Firebase service account key file (`key.json`) in this directory.
  Make sure that backend/services/firebase/config.py uses the same file name as your JSON key.

---

## 3. Input Data Setup
- Place the `output` folders (e.g., SNU CSE, Hansung Univ., company pages) inside `data/input`.
  Example:
    ```
    /data/input/{sun_cse_page_id}/output
    /data/input/{hansung_uni_page_id}/output
    /data/input/{company_page_id}/output
    ```
    
- Each `data/input/{page_id}` folder must contain its own `.env` file with your OpenAI API key:
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

- This project will **not run without OpenAI API key and Firebase configuration**.
- Do **not share API keys or JSON files**; keep them local.

---

## Common Issues

- **Blank page in the frontend**  
  This usually indicates a Firebase configuration error. Check your `.env` file and restart the app.

- **"Failed to get a response"**  
  This usually indicates an OpenAI API key issue. Check your `.env` key values.

- **Input data not recognized**
  Make sure your `output` folders are inside `data/input/{page_id}` and that each has a `.env` file.
