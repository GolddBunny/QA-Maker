import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import "../../styles/Sidebar.css";
import { usePageContext } from '../../utils/PageContext';
import { useQAHistoryContext } from '../../utils/QAHistoryContext';

function Sidebar({ isSidebarOpen, toggleSidebar }) {
    const navigate = useNavigate();
    const location = useLocation();
    const { currentPageId } = usePageContext();
    const { qaHistory, deleteQA } = useQAHistoryContext();
    
    // 삭제 모달 상태 관리
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [deleteTargetId, setDeleteTargetId] = useState(null);
    
    // 현재 페이지의 QA 히스토리만 필터링
    const currentPageQAs = qaHistory;

    // QA 항목 클릭 시 해당 대화로 이동
    const handleQAClick = (qaId) => {
        navigate(`/chat?qaId=${qaId}`);
    };

    // 삭제 모달 열기
    const openDeleteModal = (e, qaId) => {
        setDeleteTargetId(qaId);
        setDeleteModalOpen(true);
    };
    
    // 삭제 모달 닫기
    const closeDeleteModal = () => {
        setDeleteModalOpen(false);
        setDeleteTargetId(null);
    };
    
    // 삭제 확인
    const handleDeleteConfirm = () => {
        if (deleteTargetId) {
            deleteQA(deleteTargetId);
            
            // 현재 보고 있는 QA가 삭제되면 채팅 페이지로 리디렉션
            const params = new URLSearchParams(location.search);
            const currentQaId = params.get('qaId');
            if (currentQaId === deleteTargetId) {
                navigate('/chat');
            }
        }
        closeDeleteModal();
    };

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
                <div className="sidebar-close-btnX" onClick={toggleSidebar}>
                x
                </div>
            )}
            
            <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
                <div className="sidebar-header">
                    <h3>대화 기록</h3>
                </div>
                
                <div className="qa-history-list">
                    {currentPageQAs.length > 0 ? (
                        Object.entries(
                            currentPageQAs.reduce((acc, qa) => {
                                const date = new Date(qa.timestamp);
                                const today = new Date();
                                const yesterday = new Date();
                                yesterday.setDate(today.getDate() - 1);

                                const dateKey = date.toISOString().split('T')[0];

                                if (!acc[dateKey]) acc[dateKey] = [];
                                acc[dateKey].push(qa);
                                return acc;
                            }, {})
                        )
                        .sort(([dateA], [dateB]) => new Date(dateB) - new Date(dateA))
                        .map(([dateKey, qas]) => {
                            const labelDate = new Date(dateKey);
                            const today = new Date();
                            const yesterday = new Date();
                            yesterday.setDate(today.getDate() - 1);

                            let dateLabel;
                            if (labelDate.toDateString() === today.toDateString()) {
                                dateLabel = '오늘';
                            } else if (labelDate.toDateString() === yesterday.toDateString()) {
                                dateLabel = '어제';
                            } else {
                                dateLabel = `${labelDate.getMonth() + 1}월 ${labelDate.getDate()}일`;
                            }
                            const sortedQAs = [...qas].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

                            return (
                            <div key={dateKey} className="qa-date-group">
                                <div className="qa-date-label">{dateLabel}</div>
                                {sortedQAs.map((qa) => (
                                <div
                                    key={qa.id}
                                    className={`qa-history-item ${location.search.includes(`qaId=${qa.id}`) ? 'active' : ''}`}
                                    onClick={() => handleQAClick(qa.id)}
                                >
                                    <div className="qa-history-content">
                                    <div className="qa-history-question">
                                        {qa.question.length > 20 ? qa.question.slice(0, 20) + '...' : qa.question}
                                    </div>
                                    <div className="qa-item-header">
                                        <button
                                        className="delete-button"
                                        onClick={(e) => openDeleteModal(e, qa.id)}
                                        >
                                        ×
                                        </button>
                                    </div>
                                    </div>
                                </div>
                                ))}
                            </div>
                            );
                        })
                    ) : (
                        <div className="no-history-message">
                            아직 대화 기록이 없습니다.
                        </div>
                    )}
                </div>
            </div>
            
            {deleteModalOpen && (
                <div className="modal">
                    <div className="modal-content">
                        <p>이 대화를 삭제하시겠습니까?</p>
                        <div className="modal-buttons">
                            <button onClick={handleDeleteConfirm}>삭제</button>
                            <button onClick={closeDeleteModal}>취소</button>
                        </div>
                    </div>
                </div>
            )}
            </div>
        </div>
    );
}

export default Sidebar;