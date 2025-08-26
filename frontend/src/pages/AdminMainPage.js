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

    // 새 Q&A 페이지 추가
    const handleQuickAddPage = () => {
        handleAddPage();
    };

    // 클릭된 페이지로 이동
    const handlePageClick = (pageId) => {
        localStorage.setItem('currentPageId', pageId);
        setCurrentPageId(pageId);
        navigate(`/admin/${pageId}`); // 해당 페이지로 네비게이션
    };

  return (
    <div className="admin-main-container">
      <div className="main-content">
        {/* 메인 타이틀 */}
        <h1 className="title">QA Maker</h1>
        
        {/* 서비스 소개 */}
        <p className="subtitle">
          GraphRAG 기술로 웹 사이트와 문서를 지식 그래프로 구조화하여 정확한 자연어 질의응답 시스템을 몇 분 만에 구축할 수 있습니다.
        </p>
        
        {/* 주요 기능 소개 섹션 */}
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
        
        {/* Q&A 생성, 오픈 버튼 */}
        <div className="action-buttons">
          {/* 새로운 Q&A 시스템 생성 버튼 */}
          <div className="action-button get-started" onClick={handleQuickAddPage}>
            <div className="button-icon-adminMain">▷</div>
            <div className="button-content">
              <div className="button-title">Get Started</div>
              <div className="button-description">새 Q&A 시스템을 생성합니다.</div>
            </div>
          </div>
          
          {/* 기존 메인 페이지 열기 버튼 */}
          <div className="action-button open-page"
                onClick={() => {
                    const mainPage = findMainPage(); // 메인 타입 페이지 찾기
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
        
        {/* 페이지 리스트 섹션 */}
        <div className="organization-section">
          {/* 최근 생성된 6개 페이지 미리보기 */}
          {pages.slice(0,6).map((page) => (
            <div
              key={page.id}
              className="org-item"
              onClick={() => handlePageClick(page.id)} // 클릭 시 해당 페이지로 이동
            >
              <div className="org-circle">
                <div className="org-icon">📘</div> {/* 아이콘은 필요 시 변경 가능 */}
              </div>
              <div className="org-name">{page.name}</div>
            </div>
          ))}

          {/* 새로운 시스템 추가 버튼 */}
          <div className="org-item">
            <div className="org-circle add-button" onClick={handleQuickAddPage}>
              <div className="plus-icon">+</div>
            </div>
          </div>
        </div>
      </div>

      {/* 푸터 */}
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