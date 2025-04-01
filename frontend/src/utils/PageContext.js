import React, { createContext, useState, useContext } from "react";

// PageContext 생성
const PageContext = createContext();

// PageContextProvider 컴포넌트
export const PageProvider = ({ children }) => {
  const [currentPageId, setCurrentPageId] = useState("");

  return (
    <PageContext.Provider value={{ currentPageId, setCurrentPageId }}>
      {children}
    </PageContext.Provider>
  );
};

// PageContext를 사용하는 커스텀 훅
export const usePageContext = () => useContext(PageContext);