import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import "../styles/DashBoardPage.css";
import NetworkChart from "../components/charts/NetworkChart";
import { usePageContext } from '../utils/PageContext';
import { useQAHistoryContext } from '../utils/QAHistoryContext';
import { fetchEntities, fetchRelationships } from '../api/AllParquetView';
import { fetchGraphData } from '../api/AdminGraph';
import { EntityTable, RelationshipTable } from '../components/hooks/ResultTables';
import { fetchSavedUrls as fetchSavedUrlsApi } from '../api/UrlApi';

const BASE_URL = 'http://localhost:5000';

const DashboardPage = () => {
    const navigate = useNavigate();
    const { pageId } = useParams();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    
    const [activeTab, setActiveTab] = useState("entity");
    const [entities, setEntities] = useState([]);
    const [relationships, setRelationships] = useState([]);
    const [entitySearchTerm, setEntitySearchTerm] = useState("");
    const [relationshipSearchTerm, setRelationshipSearchTerm] = useState("");
    const [isSearchHovered, setIsSearchHovered] = useState(false);
    const [graphData, setGraphData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [graphError, setGraphError] = useState(null);
    const [dataFetchError, setDataFetchError] = useState(null);
    const [showGraph, setShowGraph] = useState(true);
    const graphDataCacheRef = useRef({});
    
    // URL과 문서 목록 상태 추가
    const [uploadedUrls, setUploadedUrls] = useState([]);
    const [uploadedDocs, setUploadedDocs] = useState([]);
    
    const { currentPageId, domainName, setDomainName, systemName, setSystemName } = usePageContext();
    const { qaHistory, loading: qaLoading, error: qaError } = useQAHistoryContext(currentPageId);

    const DashboardHeader = ({ isSidebarOpen, toggleSidebar }) => {
        return (
            <header className="dashboard-header">
                <div className="dashboard-header-content">
                    <div className="dashboard-header-left">
                        <button 
                            className="back-button"
                            onClick={() => navigate('/admin')}
                            title="관리자 페이지로 돌아가기"
                        >
                            ← 돌아가기
                        </button>
                        <div className="dashboard-logo-section">
                            <h1 className="dashboard-title">한성대 QA System dashboard</h1>
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

    // URL 목록 불러오기
    const fetchSavedUrls = useCallback(async (pageId) => {
        const urls = await fetchSavedUrlsApi(pageId);
        setUploadedUrls(urls);
    }, []);

    // 문서 정보 로드
    const loadDocumentsInfo = useCallback(async (id) => {
        if (!id) return;
        
        try {
            const res = await fetch(`${BASE_URL}/documents/${id}`);
            const data = await res.json();

            if (data.success) {
                const uploaded = data.uploaded_files;
                setUploadedDocs(uploaded);
            } else {
                console.error("문서 목록 로드 실패:", data.error);
            }
        } catch (error) {
            console.error("문서 정보 로드 실패:", error);
        }
    }, []);

    // 모든 데이터 로드
    const loadAllData = useCallback(async (id) => {
        if (!id) return;
        
        setLoading(true);
        setDataFetchError(null);
        
        try {
            // 병렬로 데이터 로드
            const [entitiesData, relationshipsData] = await Promise.all([
                fetchEntities(id, setDataFetchError),
                fetchRelationships(id, setDataFetchError)
            ]);
            
            // 데이터 설정
            if (entitiesData) setEntities(entitiesData);
            if (relationshipsData) setRelationships(relationshipsData);
            
        } catch (error) {
            console.error("데이터 로드 중 오류 발생:", error);
            setDataFetchError("데이터 로드 중 오류가 발생했습니다.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!pageId) {
            const savedPages = JSON.parse(localStorage.getItem("pages")) || [];
            if (savedPages.length > 0) {
                const fallbackPageId = savedPages[0].id;
                navigate(`/dashboard/${fallbackPageId}`);
            }
            return;
        }
        
        console.log("현재 dashboard pageId:", pageId);

        // 페이지 ID가 유효한 경우에만 데이터 로드
        if (pageId) {
            Promise.all([
                loadAllData(pageId),
                fetchGraphData({
                    pageId,
                    graphDataCacheRef,
                    setGraphData
                }),
                // URL과 문서 목록 로드 추가
                fetchSavedUrls(pageId),
                loadDocumentsInfo(pageId),
            ]).catch(error => {
                console.error("데이터 로드 중 오류:", error);
            });

            // 페이지 정보 불러오기
            const pages = JSON.parse(localStorage.getItem('pages')) || [];
            const currentPage = pages.find(page => page.id === pageId);
            if (currentPage) {
                setDomainName(currentPage.name || "");
                setSystemName(currentPage.sysname || "");
            }
        }
    }, [pageId, loadAllData, navigate, fetchSavedUrls, loadDocumentsInfo]);
    const filteredEntities = (entities || [])
        .filter((item) =>
            item.title && item.title.toLowerCase().includes(entitySearchTerm.toLowerCase())
        )
        .sort((a, b) => a.id - b.id);

    const filteredRelationships = (relationships || [])
        .filter(
            (item) =>
                item.description &&
                item.description.toLowerCase().includes(relationshipSearchTerm.toLowerCase())
        )
        .sort((a, b) => a.id - b.id);

    return (
        <div className={`dashboard-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
            <DashboardHeader isSidebarOpen={isSidebarOpen} />
            
            {/* 통계 섹션 */}
            <div className="stats-section">
                <div className="stats-grid">
                    <div className="stat-card url-card">
                        <div className="stat-header">
                            <span className="stat-icon">🌐</span>
                            <span className="stat-change positive">+23</span>
                        </div>
                        <div className="stat-number">1,247</div>
                        <div className="stat-label">등록된 URL</div>
                    </div>
                    
                    <div className="stat-card docs-card">
                        <div className="stat-header">
                            <span className="stat-icon">📄</span>
                            <span className="stat-change positive">+156</span>
                        </div>
                        <div className="stat-number">2,843</div>
                        <div className="stat-label">수집된 문서</div>
                    </div>
                    
                    <div className="stat-card entities-card">
                        <div className="stat-header">
                            <span className="stat-icon">🔗</span>
                            <span className="stat-change positive">+802</span>
                        </div>
                        <div className="stat-number">28,391</div>
                        <div className="stat-label">추출된 엔티티</div>
                    </div>
                    
                    <div className="stat-card relations-card">
                        <div className="stat-header">
                            <span className="stat-icon">⚡</span>
                            <span className="stat-change positive">+1,445</span>
                        </div>
                        <div className="stat-number">52,743</div>
                        <div className="stat-label">구축된 관계</div>
                    </div>
                    
                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">⏰</span>
                            <span className="stat-change positive">방금</span>
                        </div>
                        <div className="stat-number">2시간 전</div>
                        <div className="stat-label">마지막 업데이트</div>
                    </div>
                </div>
            </div>

            <div className={`dashboard-content ${isSidebarOpen ? 'sidebar-open' : ''}`}>
                
                {/* URL 리스트 섹션 개선 */}
                <div className="url-list-section">
                    <div className="section-header">
                        <h2 className="section-title-with-icon">
                            <span className="icon">🌐</span>
                            URL 리스트
                        </h2>
                        <div className="search-box">
                            <span className="search-icon">🔍</span>
                            <input 
                                type="text" 
                                placeholder="URL에서 도메인으로 검색..."
                            />
                        </div>
                    </div>
                    
                    <div className="url-table-container">
                        <div className="table-scroll-wrapper">
                            <table className="url-table">
                                <thead>
                                    <tr>
                                        <th>URL</th>
                                        <th>설명</th>
                                        <th>수집일</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {uploadedUrls.length > 0 ? (
                                        uploadedUrls.map((item, idx) => (
                                            <tr key={idx}>
                                                <td>
                                                    <a href={item.url} className="url-link" target="_blank" rel="noopener noreferrer">
                                                        {item.url}
                                                    </a>
                                                </td>
                                                <td>
                                                    <div className="url-summary">
                                                        {item.description || ""}
                                                    </div>
                                                </td>
                                                <td>
                                                    <span className="date-text">{item.date}</span>
                                                </td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr>
                                            <td colSpan="3" className="empty-state">
                                                <div className="empty-icon">📭</div>
                                                <div>등록된 URL이 없습니다.</div>
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
                
                <div className="document-section">
                    <div className="section-header">
                        <h2 className="section-title-with-icon">
                            <span className="icon">📄</span>
                            문서 목록
                        </h2>
                        <div className="search-box">
                            <span className="search-icon">🔍</span>
                            <input 
                                type="text" 
                                placeholder="문서명으로 검색..."
                            />
                        </div>
                    </div>
                    
                    <div className="url-table-container">
                        <div className="table-scroll-wrapper">
                            <table className="url-table">
                                <thead>
                                    <tr>
                                        <th>문서 이름</th>
                                        <th>카테고리</th>
                                        <th>업로드 날짜</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {uploadedDocs.length > 0 ? (
                                        uploadedDocs.map((doc, index) => (
                                            <tr key={index}>
                                                <td>
                                                    <span className="url-link">{doc.original_filename}</span>
                                                </td>
                                                <td>
                                                    <span className="category-pill">{doc.category}</span>
                                                </td>
                                                <td>
                                                    <span className="date-text">{doc.date}</span>
                                                </td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr>
                                            <td colSpan="3" className="empty-state">
                                                <div className="empty-icon">📭</div>
                                                <div>등록된 문서가 없습니다.</div>
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* QA 시스템 정보 보기 섹션 수정 */}
                <div className="result-table-section" id="info">
                    <div className="section-header">
                        <h2 className="section-title-with-icon">
                            <span className="icon">🧠</span>
                            지식 그래프 엔티티 & 관계
                        </h2>
                        <div className="header-controls">
                            <div className="result-tabs">
                                <button
                                    className={`tab ${activeTab === "entity" ? "active" : ""}`}
                                    onClick={() => setActiveTab("entity")}
                                >
                                    entity
                                </button>
                                <button
                                    className={`tab ${activeTab === "relationship" ? "active" : ""}`}
                                    onClick={() => setActiveTab("relationship")}
                                >
                                    relationship
                                </button>
                            </div>
                            <div className="search-controls">
                                <div className="search-box">
                                    <span className="search-icon">🔍</span>
                                    <input
                                        type="text"
                                        placeholder={
                                            activeTab === "entity" ? "title로 검색" : "description 내용 검색"
                                        }
                                        value={activeTab === "entity" ? entitySearchTerm : relationshipSearchTerm}
                                        onChange={(e) =>
                                            activeTab === "entity"
                                                ? setEntitySearchTerm(e.target.value)
                                                : setRelationshipSearchTerm(e.target.value)
                                        }
                                    />
                                </div>
                                <div className="entity-count">
                                    {activeTab === "entity"
                                        ? `총 엔티티 수: ${filteredEntities.length}`
                                        : `총 엣지 수: ${filteredRelationships.length}`}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div className="url-table-container">
                    {loading ? (
                        <div className="loading-message">데이터를 불러오는 중...</div>
                    ) : dataFetchError ? (
                        <div className="error-message">{dataFetchError}</div>
                    ) : (
                        <div className="table-scroll-wrapper">
                            <table className="url-table">
                                <thead>
                                    <tr>
                                        {activeTab === "entity" ? (
                                            <>
                                                <th>ID</th>
                                                <th>Title</th>
                                                <th>Description</th>
                                            </>
                                        ) : (
                                            <>
                                                <th>ID</th>
                                                <th>Source</th>
                                                <th>Target</th>
                                                <th>Description</th>
                                            </>
                                        )}
                                    </tr>
                                </thead>
                                <tbody>
                                    {activeTab === "entity" ? (
                                        filteredEntities.length > 0 ? (
                                            filteredEntities.map((entity, index) => (
                                                <tr key={index}>
                                                    <td>
                                                        <span className="entity-id">{entity.id}</span>
                                                    </td>
                                                    <td>
                                                        <span className="url-link">{entity.title}</span>
                                                    </td>
                                                    <td>
                                                        <div className="url-summary">{entity.description}</div>
                                                    </td>
                                                </tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan="3" className="empty-state">
                                                    <div className="empty-icon">🔍</div>
                                                    <div>엔티티가 없습니다.</div>
                                                </td>
                                            </tr>
                                        )
                                    ) : (
                                        filteredRelationships.length > 0 ? (
                                            filteredRelationships.map((relationship, index) => (
                                                <tr key={index}>
                                                    <td>
                                                        <span className="entity-id">{relationship.id}</span>
                                                    </td>
                                                    <td>
                                                        <span className="url-link">{relationship.source}</span>
                                                    </td>
                                                    <td>
                                                        <span className="url-link">{relationship.target}</span>
                                                    </td>
                                                    <td>
                                                        <div className="url-summary">{relationship.description}</div>
                                                    </td>
                                                </tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan="4" className="empty-state">
                                                    <div className="empty-icon">⚡</div>
                                                    <div>관계가 없습니다.</div>
                                                </td>
                                            </tr>
                                        )
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
                </div>
                {/* 그래프 보기 섹션 수정 */}
                <div className="graph-section">
                    <div className="graph-header">
                        <h2 className="section-title-with-icon">
                            🕸️ 지식그래프 네트워크 시각화 (Top 200 엔티티)
                        </h2>
                    </div>
                    {showGraph && graphData && (
                        <div className="url-table-container">
                            <div className="network-chart-wrapper">
                                <NetworkChart data={graphData} />
                            </div>
                        </div>
                    )}
                </div>
        </div>
    );
};

export default DashboardPage;