const BASE_URL = 'http://localhost:5000/flask';

export const checkOutputFolder = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/has-output/${pageId}`);
    const data = await response.json();

    if (data.success) {
      return data.has_output;
    } else {
      console.warn("서버가 output 폴더 상태를 반환하지 않음.");
      return null;
    }
  } catch (err) {
    console.error("Output 폴더 확인 실패:", err);
    return null;
  }
};