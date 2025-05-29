const BASE_URL = 'http://localhost:5000/flask';

export const processDocuments = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/process-documents/${pageId}`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      return { 
        success: true,
        results: {
          executionTime: data.execution_time,
          message: '문서 구조화 완료'
        }
      };
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
      console.log("firebase 업로드 된 총 문서 수 count: ", data.total_count);
      return {
        docs: data.uploaded_files,
        count: data.total_count || 0
      };
    } else {
      console.error("문서 목록 로드 실패:", data.error);
      return { docs: [], count: 0 };
    }
  } catch (error) {
    console.error("Firebase 문서 목록 요청 중 오류:", error);
        return { docs: [], count: 0 };
  }
};

export const createUpdatedQaHistory = (qaHistory, qaId, index, originalFilenames) => {
    const newHistory = [...qaHistory];
    const qaItemIndex = newHistory.findIndex(item => item.id === qaId);
    if (qaItemIndex !== -1) {
        const qaItem = { ...newHistory[qaItemIndex] };
        const conversations = [...qaItem.conversations];
        if (conversations[index]) {
            conversations[index] = {
                ...conversations[index],
                originalFilenames
            };
            qaItem.conversations = conversations;
            newHistory[qaItemIndex] = qaItem;
        }
    }
    return newHistory;
};