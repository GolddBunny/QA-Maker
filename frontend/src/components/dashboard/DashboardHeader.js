import React from 'react';

export const DashboardHeader = ({ isSidebarOpen, toggleSidebar, navigate, pageId }) => {
    return (
        <header className="dashboard-header">
            <div className="dashboard-header-content">
                <div className="dashboard-header-left">
                    <button 
                        className="back-button"
                        onClick={() => navigate(`/admin/${pageId}`)}
                        title="관리자 페이지로 돌아가기"
                    >
                        ← 돌아가기
                    </button>
                    <div className="dashboard-logo-section">
                        <h1 className="dashboard-title">Log Analyzer</h1>
                    </div>
                </div>
                
                <div className="dashboard-header-right">
                    <div className="dashboard-nav-links">
                        <a href="/" className="dashboard-nav-link">QA 시스템</a>
                    </div>
                </div>
            </div>
        </header>
    );
};