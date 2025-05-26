const BASE_URL = 'http://localhost:5000';

export const fetchSavedUrls = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/get-urls/${pageId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();

    if (data.success) {
      return data.urls || [];
    } else {
      console.error('URL 목록 불러오기 실패:', data.error);
      return [];
    }
  } catch (error) {
    console.error('URL 목록 불러오기 오류:', error);
    return [];
  }
};

export const uploadUrl = async (pageId, url) => {
  try {
    console.log("pageId:", pageId);
    const response = await fetch(`${BASE_URL}/add-url/${pageId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    });

    const data = await response.json();
    if (data.success) {
      return { success: true, urls: data.urls };
    } else {
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error("URL 업로드 API 오류:", error);
    return { success: false, error: error.message };
  }
};