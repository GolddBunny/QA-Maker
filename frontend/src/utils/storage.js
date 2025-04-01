// 로컬 스토리지 관련 유틸리티 함수

// 페이지 목록 가져오기
export const getPages = () => {
  try {
    return JSON.parse(localStorage.getItem('pages')) || [];
  } catch (error) {
    console.error('페이지 목록 가져오기 실패:', error);
    return [];
  }
};

// 페이지 목록 저장하기
export const savePages = (pages) => {
  try {
    localStorage.setItem('pages', JSON.stringify(pages));
    return true;
  } catch (error) {
    console.error('페이지 목록 저장 실패:', error);
    return false;
  }
};

// 현재 페이지 ID 가져오기
export const getCurrentPageId = () => {
  return localStorage.getItem('currentPageId');
};

// 현재 페이지 ID 설정하기
export const setCurrentPageId = (pageId) => {
  localStorage.setItem('currentPageId', pageId);
};

// 페이지 문서 목록 가져오기
export const getPageDocuments = (pageId) => {
  try {
    return JSON.parse(localStorage.getItem(`uploadedDocs_${pageId}`)) || [];
  } catch (error) {
    console.error('페이지 문서 목록 가져오기 실패:', error);
    return [];
  }
};

// 페이지 문서 목록 저장하기
export const savePageDocuments = (pageId, documents) => {
  try {
    localStorage.setItem(`uploadedDocs_${pageId}`, JSON.stringify(documents));
    return true;
  } catch (error) {
    console.error('페이지 문서 목록 저장 실패:', error);
    return false;
  }
};

// 특정 페이지 가져오기
export const getPage = (pageId) => {
  const pages = getPages();
  return pages.find(page => page.id === pageId) || null;
};

// 페이지 저장하기
export const savePage = (page) => {
  const pages = getPages();
  const index = pages.findIndex(p => p.id === page.id);
  
  if (index >= 0) {
    pages[index] = page;
  } else {
    pages.push(page);
  }
  
  return savePages(pages);
};

// 페이지 삭제하기
export const removePage = (pageId) => {
  const pages = getPages();
  const filteredPages = pages.filter(page => page.id !== pageId);
  
  // 현재 페이지가 삭제되는 경우 현재 페이지 ID 삭제
  if (getCurrentPageId() === pageId) {
    localStorage.removeItem('currentPageId');
  }
  
  return savePages(filteredPages);
}; 