const BASE_URL = 'http://localhost:5000';

export const processDocuments = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/${pageId}`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      return { success: true };
    } else {
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error("문서 처리 API 오류:", error);
    return { success: false, error: error.message };
  }
};