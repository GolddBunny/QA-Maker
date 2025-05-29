// API 통신을 담당하는 서비스 모듈
const BASE_URL = 'http://localhost:5000/flask';

// 쿼리 실행 API
export const runQuery = async (pageId, message, resMethod = 'local', resType = 'text') => {
  try {
    const response = await fetch(`${BASE_URL}/run-query`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        page_id: 1743412670027,
        message,
        resMethod,
        resType
      })
    });
    
    return await response.json();
  } catch (error) {
    console.error('쿼리 실행 중 오류:', error);
    throw error;
  }
};

// 그래프 생성 API
export const generateGraph = async (entities, relationships) => {
  try {
    const response = await fetch(`${BASE_URL}/generate-graph`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        entities,
        relationships
      })
    });
    
    return await response.json();
  } catch (error) {
    console.error('그래프 생성 중 오류:', error);
    throw error;
  }
};

// 파일 업로드 API
export const uploadDocuments = async (pageId, formData) => {
  try {
    const response = await fetch(`${BASE_URL}/upload-documents/${pageId}`, {
      method: 'POST',
      body: formData
    });
    
    return await response.json();
  } catch (error) {
    console.error('파일 업로드 중 오류:', error);
    throw error;
  }
};

// 문서 처리 API
export const processDocuments = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/process-documents/${pageId}`, {
      method: 'POST'
    });
    
    return await response.json();
  } catch (error) {
    console.error('문서 처리 중 오류:', error);
    throw error;
  }
};

// 페이지 초기화 API
export const initPage = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/init/${pageId}`, {
      method: 'POST'
    });
    
    return await response.json();
  } catch (error) {
    console.error('페이지 초기화 중 오류:', error);
    throw error;
  }
};

// 페이지 삭제 API
export const deletePage = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/delete-page/${pageId}`, {
      method: 'POST'
    });
    
    return await response.json();
  } catch (error) {
    console.error('페이지 삭제 중 오류:', error);
    throw error;
  }
};

// 업데이트 API
export const updatePage = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/update/${pageId}`, {
      method: 'POST'
    });
    
    return await response.json();
  } catch (error) {
    console.error('업데이트 중 오류:', error);
    throw error;
  }
}; 