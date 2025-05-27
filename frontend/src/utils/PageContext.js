import React, { createContext, useState, useContext, useEffect } from "react";
import { db } from '../firebase/sdk';
import { collection, doc, getDocs, setDoc, updateDoc, onSnapshot } from "firebase/firestore";

// PageContext 생성
const PageContext = createContext();

// PageContextProvider 컴포넌트
export const PageProvider = ({ children }) => {
  const [currentPageId, setCurrentPageId] = useState("");
  const [pages, setPages] = useState([]);
  const [systemName, setSystemName] = useState("");
  const [domainName, setDomainName] = useState("");
  const [loading, setLoading] = useState(true);

  // Firebase에서 페이지 목록 실시간 로드
  useEffect(() => {
    const unsubscribe = onSnapshot(collection(db, "pages"), (snapshot) => {
      try {
        const pagesData = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        setPages(pagesData);
        setLoading(false);
      } catch (error) {
        console.error('페이지 목록 로드 오류:', error);
        setPages([]);
        setLoading(false);
      }
    });

    return () => unsubscribe();
  }, []);

  // 현재 페이지 ID가 변경될 때마다 시스템명, 도메인명 업데이트
  useEffect(() => {
    if (!currentPageId) return;

    const currentPage = pages.find(page => page.id === currentPageId);
    const sysname = currentPage?.sysname || '';
    const name = currentPage?.name || '';
    setDomainName(name);
    setSystemName(sysname);
  }, [currentPageId, pages]);

  // 페이지 목록 업데이트 함수
  const updatePages = async (newPages) => {
    try {
      // Firebase에 각 페이지를 개별적으로 저장
      const promises = newPages.map(page => 
        setDoc(doc(db, "pages", page.id), page)
      );
      await Promise.all(promises);
      return true;
    } catch (error) {
      console.error('페이지 목록 업데이트 오류:', error);
      return false;
    }
  };

  // 특정 페이지 이름 업데이트 함수
  const updatePageName = async (pageId, newName) => {
    try {
      const pageRef = doc(db, "pages", pageId);
      await updateDoc(pageRef, {
        name: newName
      });

      // 현재 페이지인 경우 domainName 업데이트
      if (pageId === currentPageId) {
        setDomainName(newName);
      }

      return {
        success: true,
        updatedPage: { id: pageId, name: newName }
      };
    } catch (error) {
      console.error('페이지 이름 업데이트 오류:', error);
      return { success: false, error: error.message };
    }
  };

  // 특정 페이지의 시스템 이름 업데이트 함수
  const updatePageSysName = async (pageId, newSysName) => {
    try {
      const pageRef = doc(db, "pages", pageId);
      await updateDoc(pageRef, {
        sysname: newSysName
      });

      // 현재 페이지인 경우 systemName 업데이트
      if (pageId === currentPageId) {
        setSystemName(newSysName);
      }

      return {
        success: true,
        updatedPage: { id: pageId, sysname: newSysName }
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
    updatePageSysName,
    getCurrentPageSysName,
    systemName,
    setSystemName,
    domainName,
    setDomainName,
    loading, // 로딩 상태 추가
  };

  return (
    <PageContext.Provider value={value}>
      {children}
    </PageContext.Provider>
  );
};

// PageContext를 사용하는 커스텀 훅
export const usePageContext = () => useContext(PageContext);