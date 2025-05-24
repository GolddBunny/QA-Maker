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

export const loadUploadedDocs = async (pageId) => {
  try {
    const res = await fetch(`${BASE_URL}/documents/${pageId}`);
    const data = await res.json();
    if (data.success) {
      return data.uploaded_files;
    } else {
      console.error("문서 목록 로드 실패:", data.error);
      return [];
    }
  } catch (error) {
    console.error("Firebase 문서 목록 요청 중 오류:", error);
    return [];
  }
};