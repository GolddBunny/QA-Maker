import React from 'react';
import "../styles/AdminHeader.css";
import { usePageHandlers } from '../components/hooks/usePageHandlers';
import { usePageContext } from '../utils/PageContext';

const AdminHeader = ({ isSidebarOpen, toggleSidebar }) => {
    const { pages, updatePages, setCurrentPageId } = usePageContext();
    const { handleAddPage } = usePageHandlers(pages, updatePages, setCurrentPageId);

    const handleQuickAddPage = () => {
        handleAddPage(); // 이름은 내부에서 자동으로 생성됨
    };
  return (
    <header className="main-header">
      <div className="left-header">
        <div className="sidebar-toggle-button" onClick={toggleSidebar}>
          {!isSidebarOpen ? (
            <div className="hamburger-icon">
              <span></span>
              <span></span>
              <span></span>
            </div>
          ) : (
            <div className="sidebar-close-icon">×</div>
          )}
        </div>
        <div className="logo">QA Maker</div>
      </div>

      <nav className="nav-links">
        <a href="#name">이름</a>
        <a href="#register">URL / 문서 등록</a>
        <a href="#info">QA시스템 정보</a>
        <a href="#user-questions">유저 질문</a>
        <span className="divider-admin">|</span>
        <a onClick={handleQuickAddPage} className="add-domain-button">새 QA시스템 추가</a>
      </nav>
    </header>
  );
};

export default AdminHeader;