import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/AdminMainPage.css';
import { usePageHandlers } from '../components/hooks/usePageHandlers';
import { usePageContext } from '../utils/PageContext';
import { findMainPage } from '../utils/storage';

const AdminMainPage = () => {
    const { pages, updatePages, setCurrentPageId } = usePageContext();
    const { handleAddPage } = usePageHandlers(pages, updatePages, setCurrentPageId);
    const navigate = useNavigate();
    const handleQuickAddPage = () => {
        handleAddPage(); // 이름은 내부에서 자동으로 생성됨
    };

    const handlePageClick = (pageId) => {
        // 클릭된 페이지로 이동
        localStorage.setItem('currentPageId', pageId);
        setCurrentPageId(pageId);
        navigate(`/admin/${pageId}`); // 해당 페이지로 네비게이션
    };

  return (
    <div className="admin-main-container">
      <div className="main-content">
        <h1 className="title">QA Maker</h1>
        
        <p className="subtitle">
          GraphRAG 기술로 웹 사이트와 문서를 지식 그래프로 구조화하여 정확한 자연어 질의응답 시스템을 몇 분 만에 구축할 수 있습니다.
        </p>
        
        <div className="features">
          <div className="feature-item">
            <span className="feature-icon">✨</span>
            <span className="feature-text">자동 웹 크롤링</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🧠</span>
            <span className="feature-text">GraphRAG 지식 그래프</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">💭</span>
            <span className="feature-text">자연어 Q&A</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📊</span>
            <span className="feature-text">시각적 관계도</span>
          </div>
        </div>
        
        <div className="action-buttons">
          <div className="action-button get-started" onClick={handleQuickAddPage}>
            <div className="button-icon-adminMain">▷</div>
            <div className="button-content">
              <div className="button-title">Get Started</div>
              <div className="button-description">새 Q&A 시스템을 생성합니다.</div>
            </div>
          </div>
          
          <div className="action-button open-page"
                    onClick={() => {
                const mainPage = findMainPage();
                if (mainPage) {
                handlePageClick(mainPage.id);
                } else {
                alert('메인 타입 페이지가 존재하지 않습니다.');
                }
            }}>
            <div className="button-icon-adminMain">⚙</div>
            <div className="button-content">
              <div className="button-title">Open Page</div>
              <div className="button-description">구축된 Q&A 시스템을 모니터링합니다.</div>
            </div>
          </div>
        </div>
        
        <div className="organization-section">
        {pages.map((page) => (
            <div
            key={page.id}
            className="org-item"
            onClick={() => handlePageClick(page.id)}
            >
            <div className="org-circle">
                <div className="org-icon">📘</div> {/* 아이콘 변경 가능 */}
            </div>
            <div className="org-name">{page.name}</div>
            </div>
        ))}

        {/* 새 시스템 추가 버튼 */}
        <div className="org-item">
            <div className="org-circle add-button" onClick={handleQuickAddPage}>
            <div className="plus-icon">+</div>
            </div>
        </div>
        </div>
      </div>
      <footer className="site-footer">
          <div className="footer-content">
            <p className="team-name">© 2025 황금토끼 팀</p>
            <p className="team-members">개발자: 옥지윤, 성주연, 김민서</p>
            <p className="footer-note">본 시스템은 한성대학교 QA 시스템 구축 프로젝트의 일환으로 제작되었습니다.</p>
          </div>
        </footer>
    </div>
  );
};

export default AdminMainPage;