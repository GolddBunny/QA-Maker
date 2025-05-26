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

// 메인 타입 페이지 찾기
export const findMainPage = () => {
  const pages = getPages();
  return pages.find(page => page.type === 'main') || null;
};

// 새 페이지 생성하기
export const createPage = (name, type = 'normal') => {
  const newPageId = Date.now().toString();
  const newPage = {
    id: newPageId,
    name,
    type,
    createdAt: new Date().toISOString()
  };
  
  const pages = getPages();
  
  // 만약 type이 'main'이고 다른 'main' 타입 페이지가 있다면
  // 기존 main 타입 페이지를 normal로 변경
  if (type === 'main') {
    const updatedPages = pages.map(page => 
      page.type === 'main' ? { ...page, type: 'normal' } : page
    );
    updatedPages.push(newPage);
    savePages(updatedPages);
  } else {
    pages.push(newPage);
    savePages(pages);
  }
  
  return newPage;
};

// 페이지 타입 변경하기
export const changePageType = (pageId, newType) => {
  const pages = getPages();
  
  // 타입을 'main'으로 변경하는 경우, 기존 main 타입 페이지를 normal로 변경
  if (newType === 'main') {
    const updatedPages = pages.map(page => 
      page.type === 'main' ? { ...page, type: 'normal' } : page
    );
    
    const pageIndex = updatedPages.findIndex(page => page.id === pageId);
    if (pageIndex !== -1) {
      updatedPages[pageIndex] = { ...updatedPages[pageIndex], type: newType };
      return savePages(updatedPages);
    }
  } else {
    const pageIndex = pages.findIndex(page => page.id === pageId);
    if (pageIndex !== -1) {
      pages[pageIndex] = { ...pages[pageIndex], type: newType };
      return savePages(pages);
    }
  }
  
  return false;
};

// 특정 페이지 가져오기
export const getPage = (pageId) => {
  const pages = getPages();
  return pages.find(page => page.id === pageId) || null;
};

// 페이지 저장하기
export const savePage = (page) => {
  let pages = getPages();
  const index = pages.findIndex(p => p.id === page.id);

  if (page.type === 'main') {
    // 모든 페이지의 type을 'normal'로 초기화
    pages = pages.map(p => ({
      ...p,
      type: p.id === page.id ? 'main' : 'normal'
    }));
  } else {
    // 그냥 업데이트만
    if (index >= 0) {
      pages[index] = page;
    } else {
      pages.push(page);
    }
  }

  return savePages(pages);
};

// 페이지 삭제하기
export const removePage = (pageId) => {
  const pages = getPages();
  const pageToRemove = pages.find(page => page.id === pageId);
  const filteredPages = pages.filter(page => page.id !== pageId);
  
  // 현재 페이지가 삭제되는 경우 현재 페이지 ID 삭제
  if (getCurrentPageId() === pageId) {
    localStorage.removeItem('currentPageId');
  }

  // main 타입 페이지가 삭제되는 경우, 다른 페이지를 main으로 설정
  if (pageToRemove && pageToRemove.type === 'main' && pages.length > 1) {
    const filteredPages = pages.filter(page => page.id !== pageId);
    // 첫 번째 페이지를 main으로 설정
    filteredPages[0] = { ...filteredPages[0], type: 'main' };
    return savePages(filteredPages);
  }
  
  return savePages(filteredPages);
}; 