import BASE_URL from "../config/url";  

// 특정 페이지에 대해 output 폴더가 존재하는지 확인하는 함수
export const checkOutputFolder = async (pageId) => {
  try {
    // 서버에 output 폴더 존재 여부 요청
    const response = await fetch(`${BASE_URL}/has-output/${pageId}`);
    const data = await response.json();

    // 서버가 성공적으로 응답했으면 결과 반환
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