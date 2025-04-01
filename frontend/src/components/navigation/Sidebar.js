import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import "../../styles/Sidebar.css";

function Sidebar({ isSidebarOpen, toggleSidebar }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [pages, setPages] = useState([]);

    useEffect(() => {
        // 로컬 스토리지에서 페이지 목록 불러오기
        const savedPages = JSON.parse(localStorage.getItem('pages')) || [];
        setPages(savedPages);
    }, []);

    const handlePageClick = (pageId) => {
        //이 페이지에 해당하는 parquet 파일로 바꿔야함.
    };

    return (
        <div>
            <div className={`hamburger-icon ${isSidebarOpen ? 'rotate' : ''}`} onClick={toggleSidebar}>
                <span className="bar"></span>
                <span className="bar"></span>
                <span className="bar"></span>
            </div>

            <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
            <div className="page-list">
                    {pages.length > 0 ? (
                        pages.map((page) => (
                            <div
                                key={page.id}
                                className={`page-item ${location.pathname === `/admin/${page.id}` ? 'active' : ''}`}
                                onClick={() => handlePageClick(page.id)}
                            >
                                {page.name}
                            </div>
                        ))
                    ) : (
                        <div>페이지가 없습니다.</div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default Sidebar; 