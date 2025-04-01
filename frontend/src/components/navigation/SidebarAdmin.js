import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import "../../styles/Sidebar.css";

const BASE_URL = 'http://localhost:5000';

function SidebarAdmin({ isSidebarOpen, toggleSidebar }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [pages, setPages] = useState([]);
    const [newPageName, setNewPageName] = useState('');
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [selectedPageId, setSelectedPageId] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

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
        }
    }, [navigate]);

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
                        localStorage.setItem('currentPageId', nextPage.id);
                        navigate(`/admin/${nextPage.id}`);
                    } else {
                        localStorage.removeItem('currentPageId');
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

    return (
        <div>
            <div className={`hamburger-icon ${isSidebarOpen ? 'rotate' : ''}`} onClick={toggleSidebar}>
                <span className="bar"></span>
                <span className="bar"></span>
                <span className="bar"></span>
            </div>

            <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
                <input
                    type="text"
                    placeholder="새 페이지 이름"
                    value={newPageName}
                    onChange={(e) => setNewPageName(e.target.value)} // 입력값 상태 처리
                    className="new-page-input"
                    disabled={isLoading}
                />
                <button onClick={handleAddPage} className="new-page-btn" disabled={isLoading || !newPageName.trim()}>
                    {isLoading ? '처리 중...' : '새 페이지 추가하기'}
                </button>

                <div className="page-list">
                    {pages.length > 0 ? (
                        pages.map((page) => (
                            <div
                                key={page.id}
                                className={`page-item ${location.pathname === `/admin/${page.id}` ? 'active' : ''}`}
                                onClick={() => handlePageClick(page.id)}
                                onContextMenu={(e) => handleRightClick(e, page.id)} // 우클릭 이벤트 추가
                            >
                                {page.name}
                            </div>
                        ))
                    ) : (
                        <div>페이지가 없습니다.</div>
                    )}
                </div>
            </div>
            {showDeleteModal && (
                <div className="modal">
                    
                    <div className="modal-buttons">
                        <button onClick={handleDeletePage} disabled={isLoading}>
                            {isLoading ? '삭제 중...' : '삭제'}
                        </button>
                        <button onClick={closeModal} disabled={isLoading}>취소</button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default SidebarAdmin; 