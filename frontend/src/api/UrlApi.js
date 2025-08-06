const BASE_URL = 'http://localhost:5000/flask';

// 저장된 URL 목록 가져오기
export const fetchSavedUrls = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/get-general-crawled-urls/${pageId}`, {
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

// 저장된 문서 URL 목록 가져오기
export const fetchSavedDocumentUrls = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/get-document-urls/${pageId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();
    console.log(`[fetchSavedDocumentUrls] 응답 데이터:`, data);

    if (data.success) {
      const urls = Array.isArray(data.urls) ? data.urls : [];
      console.log(`[fetchSavedDocumentUrls] 성공: ${urls.length}개 문서 URL 로드`);
      return urls;
    } else {
      console.error('문서 URL 목록 불러오기 실패:', data.error);
      return [];
    }
  } catch (error) {
    console.error('문서 URL 목록 불러오기 오류:', error);
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

// 3단계 텍스트 정리 - 비활성화됨
// export const line1 = async (pageId) => {
//   try {
//     console.log("UrlApi.js: 웹 크롤링 텍스트 line1 정리 시작:", pageId);
//     const response = await fetch(`${BASE_URL}/line1/${pageId}`, {
//       method: 'POST',
//       headers: {
//         'Content-Type': 'application/json',
//       }
//     });

//     const data = await response.json();
//     if (data.success) {
//       return { success: true, results: data.results };
//     } else {
//       return { success: false, error: data.error };
//     }
//   } catch (error) {
//     console.error("UrlApi.js: 웹 크롤링 텍스트 line1 정리 API 오류:", error);
//     return { success: false, error: error.message };
//   }
// };

// 4단계 문서 다운로더 - 크롤링된 문서 URL을 다운로드하여 Firebase에 저장
export const documentDownloader = async (pageId) => {
  try {
    console.log("UrlApi.js: 문서 다운로더 시작:", pageId);
    
    // 먼저 저장된 문서 URL 목록을 직접 가져오기
    const savedDocumentUrls = await fetchSavedDocumentUrls(pageId);
    if (!savedDocumentUrls || savedDocumentUrls.length === 0) {
      return { 
        success: true, 
        results: {
          message: "저장된 문서 URL이 없습니다. 다음 단계로 진행합니다.",
          stats: {
            total: 0,
            success: 0,
            failed: 0,
            skipped: 0,
            filtered_out: 0,
            firebase_uploaded: 0,
            firebase_failed: 0,
            local_deleted: 0
          },
          total_doc_urls: 0
        }
      };
    }
    
    console.log("저장된 문서 URL 데이터:", savedDocumentUrls.slice(0, 3)); // 처음 3개 요소 확인
    
    // 문서 URL 목록에서 URL 문자열만 추출
    const docUrls = savedDocumentUrls.map(urlData => {
      return typeof urlData === 'object' && urlData.url ? urlData.url : urlData;
    }).filter(url => typeof url === 'string');
    
    console.log(`문서 URL ${docUrls.length}개 발견:`, docUrls);
    
    if (docUrls.length === 0) {
      return { 
        success: true, 
        results: {
          message: "다운로드할 문서 URL이 없습니다. 다음 단계로 진행하세요.",
          stats: {
            total: 0,
            success: 0,
            failed: 0,
            skipped: 0,
            filtered_out: 0,
            firebase_uploaded: 0,
            firebase_failed: 0,
            local_deleted: 0
          },
          total_doc_urls: 0
        }
      };
    }
    
    // 크롤링된 문서 다운로드 API 호출
    const response = await fetch(`${BASE_URL}/download-crawled-documents/${pageId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ doc_urls: docUrls })
    });

    const data = await response.json();
    if (data.success) {
      return { 
        success: true, 
        results: {
          message: data.message,
          stats: data.stats,
          total_doc_urls: docUrls.length
        }
      };
    } else {
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error("UrlApi.js: 문서 다운로더 API 오류:", error);
    return { success: false, error: error.message };
  }
};