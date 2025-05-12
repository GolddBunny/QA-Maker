import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import "../../styles/Sidebar.css";
import { usePageContext } from "../../utils/PageContext";
const BASE_URL = 'http://localhost:5000';

function SidebarAdmin({ isSidebarOpen, toggleSidebar }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [pages, setPages] = useState([]);
    const [newPageName, setNewPageName] = useState('');
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [selectedPageId, setSelectedPageId] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const {currentPageId, setCurrentPageId} = usePageContext();

    useEffect(() => {
        // 로컬 스토리지에서 저장된 페이지 목록 불러오기
        let savedPages = JSON.parse(localStorage.getItem('pages')) || [];
    
        // 페이지가 없으면 기본 페이지 추가
        if (savedPages.length === 0) {
            const initDefaultPage = async () => {
                setIsLoading(true);
                const defaultPageId = Date.now().toString();
                
                try {
                    // 서버에 기본 페이지 초기화 요청
                    const response = await fetch(`${BASE_URL}/init/${defaultPageId}`, {
                        method: 'POST'
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        // 기본 페이지 추가
                        const defaultPage = {
                            id: defaultPageId,
                            name: '기본 페이지',
                        };
                        
                        savedPages = [defaultPage];
                        localStorage.setItem('pages', JSON.stringify(savedPages));

                        setCurrentPageId(defaultPageId);
                        localStorage.setItem('currentPageId', defaultPageId);
                        setPages(savedPages);
                        
                        // 기본 페이지로 이동
                        navigate(`/admin/${defaultPageId}`);
                    } else {
                        console.error('기본 페이지 초기화 실패:', data.error);
                        alert('기본 페이지 초기화에 실패했습니다.');
                    }
                } catch (error) {
                    console.error('기본 페이지 초기화 중 오류:', error);
                    alert('기본 페이지 초기화 중 오류가 발생했습니다. 서버 연결을 확인해주세요.');
                } finally {
                    setIsLoading(false);
                }
            };
    
            initDefaultPage();
        } else {
            setPages(savedPages);
            const storedCurrentPageId = localStorage.getItem('currentPageId');
            if (storedCurrentPageId) {
                setCurrentPageId(storedCurrentPageId);
            } else if (savedPages.length > 0) {
                // 저장된 currentPageId가 없는 경우 첫 번째 페이지를 현재 페이지로 설정
                setCurrentPageId(savedPages[0].id);
                localStorage.setItem('currentPageId', savedPages[0].id);
            }
        }
    }, [navigate, setCurrentPageId]);

    const handleAddPage = async() => {
        console.log('새 페이지 추가 버튼이 클릭되었습니다.');
        if (newPageName.trim()) {
            setIsLoading(true);
            const newPageId = Date.now().toString();

            try {
                // 서버에 새 페이지 초기화 요청
                const response = await fetch(`${BASE_URL}/init/${newPageId}`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // 새 페이지 추가
                    const newPage = {
                        id: newPageId,
                        name: newPageName,
                    };
                    
                    const updatedPages = [...pages, newPage];
                    setPages(updatedPages);
                    localStorage.setItem('pages', JSON.stringify(updatedPages));
                    setNewPageName('');  // 입력창 초기화
                    
                    // 새 페이지로 이동
                    localStorage.setItem('currentPageId', newPageId);
                    setCurrentPageId(newPageId);
                    navigate(`/admin/${newPageId}`);
                } else {
                    console.error('페이지 초기화 실패:', data.error);
                    alert('페이지 초기화에 실패했습니다.');
                }
            } catch (error) {
                console.error('페이지 초기화 중 오류:', error);
                alert('페이지 초기화 중 오류가 발생했습니다.');
            } finally {
                setIsLoading(false);
            }
        }
    };

    const handlePageClick = (pageId) => {
        // 클릭된 페이지로 이동
        localStorage.setItem('currentPageId', pageId);
        navigate(`/admin/${pageId}`); // 해당 페이지로 네비게이션
    };

    const handleRightClick = (e, pageId) => {
        e.preventDefault();
        setSelectedPageId(pageId);
        setShowDeleteModal(true);
    };

    const handleDeletePage = async () => {
        setIsLoading(true);
        try {
            // 서버에 페이지 삭제 요청
            const response = await fetch(`${BASE_URL}/delete-page/${selectedPageId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 로컬 상태 업데이트
                const updatedPages = pages.filter((page) => page.id !== selectedPageId);
                setPages(updatedPages);
                localStorage.setItem('pages', JSON.stringify(updatedPages));
                
                // 현재 페이지가 삭제된 페이지인 경우, 다른 페이지로 이동
                if (localStorage.getItem('currentPageId') === selectedPageId) {
                    const nextPage = updatedPages[0] || null;
                    if (nextPage) {
                        setCurrentPageId(nextPage.id);

                        localStorage.setItem('currentPageId', nextPage.id);
                        navigate(`/admin/${nextPage.id}`);
                    } else {
                        localStorage.removeItem('currentPageId');
                        setCurrentPageId(null);
                        navigate('/admin');
                    }
                }
            } else {
                console.error('페이지 삭제 실패:', data.error);
                alert('페이지 삭제에 실패했습니다.');
            }
        } catch (error) {
            console.error('페이지 삭제 중 오류:', error);
            alert('페이지 삭제 중 오류가 발생했습니다.');
        } finally {
            setShowDeleteModal(false);
            setIsLoading(false);
        }
    };

    const closeModal = () => {
        setShowDeleteModal(false);
    }

    // 선택된 페이지 정보 가져오기
    const selectedPage = pages.find(page => page.id === selectedPageId);

    return (
        <div>
            {!isSidebarOpen && (
                <div className="sidebar-toggle-button" onClick={toggleSidebar}>
                    <img
                    src="/assets/sidebar_right.png"
                    alt="사이드바 열기"
                    className="sidebar-toggle-icon"
                    />
                </div>
                )}
            <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
            {/* 열린 상태: 사이드바 내부 오른쪽 상단에 토글 이미지 */}
            {isSidebarOpen && (
                <div className="sidebar-close-button" onClick={toggleSidebar}>
                <img
                    src="/assets/sidebar_left.png"
                    alt="사이드바 닫기"
                    className="sidebar-toggle-icon"
                />
                </div>
            )}
            <div className="new-page-title"><strong>새 도메인 페이지 추가하기</strong></div>

            <div className="new-page-container">
                <input
                type="text"
                placeholder="도메인 이름을 정해주세요"
                value={newPageName}
                onChange={(e) => setNewPageName(e.target.value)}
                className="new-page-input"
                disabled={isLoading}
                />
                <button
                onClick={handleAddPage}
                className="add-page-btn"
                disabled={isLoading || !newPageName.trim()}
                >
                추가
                </button>
            </div>

            <div className="page-list-title">도메인 페이지 목록</div>

            <div className="page-list">
                {pages.length > 0 ? (
                pages.map((page) => (
                    <div
                    key={page.id}
                    className={`page-item ${location.pathname === `/admin/${page.id}` ? 'active' : ''}`}
                    onClick={() => handlePageClick(page.id)}
                    onContextMenu={(e) => handleRightClick(e, page.id)}
                    >
                    <strong>{page.name}</strong>
                    </div>
                ))
                ) : (
                <div className="no-pages-message">페이지가 없습니다.</div>
                )}
            </div>
            </div>
            {showDeleteModal && (
                <div className="modal">
                    <div className="modal-content">
                        <h3>페이지 삭제</h3>
                        <div className="modal-buttons">
                            <button onClick={handleDeletePage} disabled={isLoading}>
                                {isLoading ? '삭제 중...' : '삭제'}
                            </button>
                            <button onClick={closeModal} disabled={isLoading}>취소</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default SidebarAdmin; 