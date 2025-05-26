import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import "../../styles/Sidebar.css";
import { usePageContext } from "../../utils/PageContext";
import { savePages, getPages, changePageType } from '../../utils/storage';
import { usePageHandlers } from '../hooks/usePageHandlers';

const BASE_URL = 'http://localhost:5000';

function SidebarAdmin({ isSidebarOpen, toggleSidebar }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [newPageName, setNewPageName] = useState('');
    const [newSysName, setNewSysName] = useState('');
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [selectedPageId, setSelectedPageId] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const { pages, currentPageId, setCurrentPageId, updatePages } = usePageContext();
    const { handleAddPage } = usePageHandlers(pages, updatePages, setCurrentPageId);
    
    useEffect(() => {
        const initializePages = async () => {
            let savedPages = JSON.parse(localStorage.getItem('pages')) || [];

            if (savedPages.length === 0) {
                setIsLoading(true);
                const defaultPageId = Date.now().toString();

                try {
                    const response = await fetch(`${BASE_URL}/init/${defaultPageId}`, {
                        method: 'POST'
                    });

                    const data = await response.json();

                    if (data.success) {
                        const defaultPage = {
                            id: defaultPageId,
                            name: '기본 페이지',
                            sysname: '',
                            type: 'main',
                            createdAt: new Date().toISOString()
                        };

                        savedPages = [defaultPage];
                        localStorage.setItem('pages', JSON.stringify(savedPages));
                        localStorage.setItem('currentPageId', defaultPageId);

                        updatePages(savedPages);
                        setCurrentPageId(defaultPageId);

                        
                        navigate(`/admin/${defaultPageId}`);
                    } else {
                        console.error('기본 페이지 초기화 실패:', data.error);
                        alert('기본 페이지 초기화에 실패했습니다.');
                    }
                } catch (error) {
                    console.error('기본 페이지 초기화 중 오류:', error);
                    alert('기본 페이지 초기화 중 오류가 발생했습니다.');
                } finally {
                    setIsLoading(false);
                }
            } else {
                const updatedPages = savedPages.map(page => {
                    if (!page.hasOwnProperty('sysname')) {
                        return { ...page, sysname: '' };
                    }
                    return page;
                });
                // If pages were updated to add sysname, save them
                if (JSON.stringify(updatedPages) !== JSON.stringify(savedPages)) {
                    localStorage.setItem('pages', JSON.stringify(updatedPages));
                    updatePages(updatedPages);
                } else {
                    updatePages(savedPages);
                }

                // 저장된 현재 페이지 ID 확인
                const storedCurrentPageId = localStorage.getItem('currentPageId');
                
                // 1. 저장된 currentPageId가 있고, 해당 ID를 가진 페이지가 존재하면 그 페이지 사용
                if (storedCurrentPageId && savedPages.some(page => page.id === storedCurrentPageId)) {
                    setCurrentPageId(storedCurrentPageId);
                } 
                // 2. main 타입 페이지가 있으면 그 페이지 사용
                else {
                    const mainPage = savedPages.find(page => page.type === 'main');
                    if (mainPage) {
                        setCurrentPageId(mainPage.id);
                        localStorage.setItem('currentPageId', mainPage.id);
                        console.log("메인 타입 페이지 ID 설정:", mainPage.id);
                    }
                    // 3. 없으면 첫 번째 페이지를 main으로 설정하고 사용
                    else if (savedPages.length > 0) {
                        const firstPage = savedPages[0];
                        // 첫 번째 페이지를 main 타입으로 업데이트
                        const updatedPages = [...savedPages];
                        updatedPages[0] = { ...firstPage, type: 'main' };
                        
                        localStorage.setItem('pages', JSON.stringify(updatedPages));
                        updatePages(updatedPages);
                        
                        setCurrentPageId(firstPage.id);
                        localStorage.setItem('currentPageId', firstPage.id);
                        console.log("첫 번째 페이지를 메인으로 설정:", firstPage.id);
                    }
                }
            }
        };

        initializePages();
    }, [setCurrentPageId]);

    const handlePageClick = (pageId) => {
        // 클릭된 페이지로 이동
        localStorage.setItem('currentPageId', pageId);
        setCurrentPageId(pageId);
        navigate(`/admin/${pageId}`); // 해당 페이지로 네비게이션
    };

    const handleRightClick = (e, pageId) => {
        e.preventDefault();
        setSelectedPageId(pageId);
        setShowDeleteModal(true);
    };

    const handleSetMainPage = (pageId) => {
    console.log('handleSetMainPage 실행 - pageId:', pageId, typeof pageId);
    console.log('변경 전 pages:', pages);
    
    // pageId를 문자열로 변환하여 비교
    const targetPageId = String(pageId);
    
    const updatedPages = pages.map(page => {
        console.log('비교:', page.id, '===', targetPageId, '?', page.id === targetPageId);
        return {
            ...page,
            type: page.id === targetPageId ? 'main' : 'normal'
        };
    });
    
    console.log('변경 후 updatedPages:', updatedPages);
    
    savePages(updatedPages);
    updatePages(updatedPages);
    setShowDeleteModal(false);
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
                const pageToDelete = pages.find(page => page.id === selectedPageId);
                const isMainPage = pageToDelete?.type === 'main';

                // 로컬 상태 업데이트
                const updatedPages = pages.filter((page) => page.id !== selectedPageId);

                // 만약 main 페이지가 삭제되었고 다른 페이지가 있다면 첫 번째 페이지를 main으로 설정
                if (isMainPage && updatedPages.length > 0) {
                    updatedPages[0] = { ...updatedPages[0], type: 'main' };
                }
                updatePages(updatedPages);
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

    return (
        <div>
            <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
            <div className="new-page-title"><strong>새 QA 시스템 추가하기</strong></div>

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

            <div className="page-list-title">QA 시스템 목록</div>

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
                        <button 
                            className="set-main-button" 
                            onClick={() => handleSetMainPage(selectedPageId)}
                        >
                            메인으로 설정
                        </button>
                        <h3 style={{ textAlign: 'center' }}>페이지 삭제</h3>
                        
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