const BASE_URL = 'http://localhost:5000/flask';

// 특정 페이지의 문서를 서버에서 구조화 처리하는 함수
export const processDocuments = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/process-documents/${pageId}`, {
      method: 'POST'
    });

    const data = await response.json();

    if (data.success) {
      // 처리 성공 시 실행 시간과 메시지를 반환
      return { 
        success: true,
        results: {
          executionTime: data.execution_time,
          message: '문서 구조화 완료'
        }
      };
    } else {
      return { success: false, error: data.error,executionTime: data.execution_time };
    }
  } catch (error) {
    console.error("문서 처리 API 오류:", error);
    return { success: false, error: error.message };
  }
};

// Firebase에 업로드된 문서 목록을 불러오는 함수
export const loadUploadedDocs = async (pageId) => {
  try {
    const res = await fetch(`${BASE_URL}/documents/${pageId}`);
    const data = await res.json();
    if (data.success) {
      console.log("firebase 업로드 된 총 문서 수 count: ", data.total_count);
      // 문서 리스트와 총 개수 반환
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

// QA 히스토리에서 특정 대화 항목에 원본 파일명 정보를 업데이트하는 함수
export const createUpdatedQaHistory = (qaHistory, qaId, index, originalFilenames) => {
    const newHistory = [...qaHistory];  // 원본 배열 복사
    const qaItemIndex = newHistory.findIndex(item => item.id === qaId); // 해당 QA 항목 찾기
    if (qaItemIndex !== -1) {
        const qaItem = { ...newHistory[qaItemIndex] };  // 해당 QA 항목 복사
        const conversations = [...qaItem.conversations];  // 대화 배열 복사
        if (conversations[index]) {
            // 지정된 인덱스의 대화에 originalFilenames 정보 추가
            conversations[index] = {
                ...conversations[index],
                originalFilenames
            };
            qaItem.conversations = conversations; // 수정된 대화 배열 반영
            newHistory[qaItemIndex] = qaItem; // QA 항목 갱신
        }
    }
    return newHistory;
};