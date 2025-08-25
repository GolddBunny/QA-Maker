const BASE_URL = 'http://localhost:5000/flask';

// 특정 페이지의 문서 URL 초기화를 요청하는 함수
export const initDocUrl = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/init_doc_url/${pageId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();

    if (data.success) {
      return { success: true, message: data.message };
    } else {
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error("init_doc_url API 오류:", error);
    return { success: false, error: error.message };
  }
};