const BASE_URL = 'http://localhost:5000/flask';

// 저장된 URL 목록 가져오기
export const fetchSavedUrls = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/get-urls/${pageId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();
    console.log(`[fetchSavedUrls] 응답 데이터:`, data);

    if (data.success) {
      const urls = Array.isArray(data.urls) ? data.urls : [];
      console.log(`[fetchSavedUrls] 성공: ${urls.length}개 URL 로드`);
      return urls;
    } else {
      console.error('URL 목록 불러오기 실패:', data.error);
      return [];
    }
  } catch (error) {
    console.error('URL 목록 불러오기 오류:', error);
    return [];
  }
};

// url 추가
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

// 1단계 URL 크롤링 시작
export const startUrlCrawling = async (pageId) => {
  try {
    console.log("URL 크롤링 시작:", pageId);
    const response = await fetch(`${BASE_URL}/start-crawling/${pageId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();
    if (data.success) {
      return { success: true, results: data.results };
    } else {
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error("URL 크롤링 API 오류:", error);
    return { success: false, error: error.message };
  }
};

// 2단계 웹 크롤링 및 구조화
export const crawlAndStructure = async (pageId) => {
  try {
    console.log("UrlApi.js: 웹 크롤링 및 구조화 시작:", pageId);
    const response = await fetch(`${BASE_URL}/crawl-and-structure/${pageId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();
    if (data.success) {
      return { success: true, results: data.results };
    } else {
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error("UrlApi.js: 웹 크롤링 및 구조화 API 오류:", error);
    return { success: false, error: error.message };
  }
};

// 3단계 텍스트 정리
export const line1 = async (pageId) => {
  try {
    console.log("UrlApi.js: 웹 크롤링 텍스트 line1 정리 시작:", pageId);
    const response = await fetch(`${BASE_URL}/line1/${pageId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();
    if (data.success) {
      return { success: true, results: data.results };
    } else {
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error("UrlApi.js: 웹 크롤링 텍스트 line1 정리 API 오류:", error);
    return { success: false, error: error.message };
  }
};