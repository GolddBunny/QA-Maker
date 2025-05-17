import React, { createContext, useState, useContext, useEffect } from "react";

// PageContext 생성
const PageContext = createContext();

// PageContextProvider 컴포넌트
export const PageProvider = ({ children }) => {
  const [currentPageId, setCurrentPageId] = useState("");
  const [pages, setPages] = useState([]);
  
  const [systemName, setSystemName] = useState("");
  const [domainName, setDomainName] = useState("");

  useEffect(() => {
    const loadPages = () => {
      try {
        const savedPages = JSON.parse(localStorage.getItem('pages')) || [];
        setPages(savedPages);
      } catch (error) {
        console.error('페이지 목록 로드 오류:', error);
        setPages([]);
      }
    };
    
    loadPages();
  }, []);

  // 현재 페이지 ID가 변경될 때마다 로컬 스토리지 업데이트
  useEffect(() => {
    if (currentPageId) {
      localStorage.setItem('currentPageId', currentPageId);
      
    }
  }, [currentPageId]);

  useEffect(() => {
    if (!currentPageId) return;

    const currentPage = pages.find(page => page.id === currentPageId);
    const sysname = currentPage.sysname || '';
    const name = currentPage.name || '';
    setDomainName(name);
    setSystemName(sysname); // 상태를 업데이트

  }, [currentPageId, pages]);

  // 페이지 목록 업데이트 함수
  const updatePages = (newPages) => {
    try {
      localStorage.setItem('pages', JSON.stringify(newPages));
      setPages(newPages);
      return true;
    } catch (error) {
      console.error('페이지 목록 업데이트 오류:', error);
      return false;
    }
  };

  // 특정 페이지 이름 업데이트 함수
  const updatePageName = (pageId, newName) => {
    try {
      const pageIndex = pages.findIndex(page => page.id === pageId);
      
      if (pageIndex === -1) {
        return { success: false, error: "페이지를 찾을 수 없습니다." };
      }
      
      // 새로운 페이지 배열 생성 (불변성 유지)
      const updatedPages = [...pages];
      updatedPages[pageIndex] = { ...updatedPages[pageIndex], name: newName };
      
      // 로컬 스토리지와 상태 업데이트
      localStorage.setItem('pages', JSON.stringify(updatedPages));
      setPages(updatedPages);
      if (pageId === currentPageId) {
        setDomainName(newName);
      }
      
      return { 
        success: true, 
        updatedPage: updatedPages[pageIndex]
      };
    } catch (error) {
      console.error('페이지 이름 업데이트 오류:', error);
      return { success: false, error: error.message };
    }
  };

  // 특정 페이지의 시스템 이름 업데이트 함수
  const updatePageSysName = (pageId, newSysName) => {
    try {
      const pageIndex = pages.findIndex(page => page.id === pageId);
      
      if (pageIndex === -1) {
        return { success: false, error: "페이지를 찾을 수 없습니다." };
      }
      
      // 새로운 페이지 배열 생성 (불변성 유지) 
      const updatedPages = [...pages];
      updatedPages[pageIndex] = { ...updatedPages[pageIndex], sysname: newSysName };
      
      // 로컬 스토리지와 상태 업데이트
      localStorage.setItem('pages', JSON.stringify(updatedPages));
      setPages(updatedPages);
      
      return {
        success: true,
        updatedPage: updatedPages[pageIndex]
      };
    } catch (error) {
      console.error('페이지 시스템 이름 업데이트 오류:', error);
      return { success: false, error: error.message };
    }
  };

  // 현재 페이지의 시스템 이름 가져오기
  const getCurrentPageSysName = () => {
    if (!currentPageId) return '';
    
    const currentPage = pages.find(page => page.id === currentPageId);
    return currentPage?.sysname || '';
  };

  // Context를 통해 제공할 값들
  const value = {
    currentPageId,
    setCurrentPageId,
    pages,
    updatePages,
    updatePageName,
    updatePageSysName, // 새로 추가된 함수
    getCurrentPageSysName, // 새로 추가된 함수
    systemName,
    setSystemName,
    domainName,
    setDomainName,
  };

  return (
    <PageContext.Provider value={value}>
      {children}
    </PageContext.Provider>
  );
};

// PageContext를 사용하는 커스텀 훅
export const usePageContext = () => useContext(PageContext);