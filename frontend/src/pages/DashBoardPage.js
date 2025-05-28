import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';

import "../styles/DashBoardPage.css";
import NetworkChart from "../components/charts/NetworkChart";
import { usePageContext } from '../utils/PageContext';
import { useQAHistoryContext } from '../utils/QAHistoryContext';
import { fetchEntities, fetchRelationships } from '../api/AllParquetView';
import { fetchGraphData } from '../api/AdminGraph';
import { EntityTable, RelationshipTable } from '../components/hooks/ResultTables';
import { fetchSavedUrls as fetchSavedUrlsApi } from '../api/UrlApi';

import { 
    loadDocumentsInfo, 
    fetchGraphBuildStats, 
    fetchKnowledgeGraphStats 
} from '../components/dashboard/dashboardDataLoaders';
import { 
    getDateStats, 
    getKnowledgeGraphDateStats, 
    getGraphBuildDateStats 
} from '../components/dashboard/dashboardStats';
import { DashboardHeader } from '../components/dashboard/DashboardHeader';

const DashboardPage = () => {
    const navigate = useNavigate();
    const { pageId } = useParams();
    const { currentPageId, domainName, setDomainName, systemName, setSystemName } = usePageContext();
    const { qaHistory, loading: qaLoading, error: qaError } = useQAHistoryContext(currentPageId);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [activeTab, setActiveTab] = useState("entity");
    const [showGraph, setShowGraph] = useState(true);
    const [loading, setLoading] = useState(true);
    const [entitySearchTerm, setEntitySearchTerm] = useState("");
    const [relationshipSearchTerm, setRelationshipSearchTerm] = useState("");
    const [isSearchHovered, setIsSearchHovered] = useState(false);
    const [entities, setEntities] = useState([]);
    const [relationships, setRelationships] = useState([]);
    const [graphData, setGraphData] = useState(null);
    const [uploadedUrls, setUploadedUrls] = useState([]);
    const [uploadedDocs, setUploadedDocs] = useState([]);
    const [graphBuildStats, setGraphBuildStats] = useState([]);
    const [knowledgeGraphStats, setKnowledgeGraphStats] = useState([]);
    const [createdDate, setCreatedDate] = useState("");
    const [graphError, setGraphError] = useState(null);
    const [dataFetchError, setDataFetchError] = useState(null);
    const [conversionTime, setConversionTime] = useState(null);
    const graphDataCacheRef = useRef({});
    const loadedRef = useRef(false); // 중복 로딩 방지
    const location = useLocation();

    const urlCount = uploadedUrls?.length || 0;
    const docCount = uploadedDocs?.length || 0;

    const loadEntities = useCallback(async (id) => {
        if (!id) return;
        
        try {
            console.log("엔티티 데이터 로드 중...");
            const entitiesData = await fetchEntities(id, setDataFetchError);
            
            if (entitiesData) {
                console.log("엔티티 데이터 로드 완료:", entitiesData.length);
                setEntities(entitiesData);
            } else {
                console.warn("엔티티 데이터가 null 또는 undefined입니다");
                setEntities([]);
            }
        } catch (error) {
            console.error("엔티티 데이터 로드 중 오류:", error);
            setDataFetchError("엔티티 데이터 로드 중 오류가 발생했습니다.");
        }
    }, []);

    const loadRelationships = useCallback(async (id) => {
        if (!id) return;
        
        try {
            console.log("🔗 관계 데이터 로드 중...");
            const relationshipsData = await fetchRelationships(id, setDataFetchError);
            
            if (relationshipsData) {
                console.log("관계 데이터 로드 완료:", relationshipsData.length);
                setRelationships(relationshipsData);
            } else {
                console.warn("관계 데이터가 null 또는 undefined");
                setRelationships([]);
            }
        } catch (error) {
            console.error("관계 데이터 로드 중 오류:", error);
            setDataFetchError("관계 데이터 로드 중 오류가 발생했습니다.");
        }
    }, []);

    const loadGraphData = useCallback(async (pageId) => {
        if (!pageId) return;
        
        try {
            await fetchGraphData({
                pageId,
                graphDataCacheRef,
                setGraphData
            });
        } catch (error) {
            console.error('그래프 데이터 로드 중 오류:', error);
            setGraphError('그래프 데이터를 불러올 수 없습니다.');
        }
    }, []);

    const fetchSavedUrls = useCallback(async (pageId) => {
        try {
            const urls = await fetchSavedUrlsApi(pageId);
            setUploadedUrls(urls);
        } catch (error) {
            console.error('URL 목록 로드 중 오류:', error);
        }
    }, []);

    const dateStats = useMemo(() => getDateStats(uploadedUrls, uploadedDocs), [uploadedUrls, uploadedDocs]);
    const knowledgeGraphDateStats = useMemo(() => getKnowledgeGraphDateStats(knowledgeGraphStats), [knowledgeGraphStats]);
    const graphDateStats = useMemo(() => getGraphBuildDateStats(graphBuildStats), [graphBuildStats]);

    const maxValue = Math.max(...dateStats.map(item => Math.max(item.url, item.doc)), 1);
    const knowledgeGraphMaxValue = Math.max(
        ...knowledgeGraphDateStats.map(item => Math.max(item.entity, item.relationship)), 
        1
    );
    const maxGraphValue = Math.max(...graphDateStats.map(item => Math.max(item.entity, item.relationship)), 1);

    // === Filtered Data ===
    const filteredEntities = useMemo(() => {
        if (!entities.length) return [];
        
        const filtered = entities
            .filter((item) => {
                const hasTitle = item.title && typeof item.title === 'string';
                const matchesSearch = hasTitle ? 
                    item.title.toLowerCase().includes(entitySearchTerm.toLowerCase()) : false;
                
                return hasTitle && matchesSearch;
            })
            .sort((a, b) => a.id - b.id);
            
        // console.log("엔티티 필터링 완료:", {
        //     filteredCount: filtered.length,
        //     removedCount: entities.length - filtered.length,
        // });
        
        return filtered;
    }, [entities, entitySearchTerm]);

    const filteredRelationships = useMemo(() => {
        if (!relationships.length) return [];
        
        const filtered = relationships
            .filter((item) => {
                const hasDescription = item.description && typeof item.description === 'string';
                const matchesSearch = hasDescription ? 
                    item.description.toLowerCase().includes(relationshipSearchTerm.toLowerCase()) : false;
                
                return hasDescription && matchesSearch;
            })
            .sort((a, b) => a.id - b.id);
            
        // console.log("관계 필터링 완료:", {
        //     filteredCount: filtered.length,
        //     removedCount: relationships.length - filtered.length,
        // });
        
        return filtered;
    }, [relationships, relationshipSearchTerm]);

    const loadPageInfo = useCallback(() => {
        const pages = JSON.parse(localStorage.getItem('pages')) || [];
        const currentPage = pages.find(page => page.id === pageId);
        console.log("📄 현재 페이지 정보:", currentPage);
        
        if (currentPage) {
            setDomainName(currentPage.name || "");
            setSystemName(currentPage.sysname || "");
            
            if (currentPage.createdAt) {
                try {
                    const date = new Date(currentPage.createdAt);
                    const year = date.getFullYear();
                    const month = String(date.getMonth() + 1).padStart(2, '0');
                    const day = String(date.getDate()).padStart(2, '0');
                    console.log('날짜 파싱 성공:', currentPage.createdAt);
                    setCreatedDate(`${year}.${month}.${day}`);
                } catch (error) {
                    console.log('날짜 파싱 실패:', currentPage.createdAt);
                    setCreatedDate("2025.05.27");
                }
            } else {
                console.log("createdAt 필드가 없으므로 기본 설정 날짜로 대신합니다.");
                setCreatedDate("2025.05.27");
            }
        } else {
            console.warn("현재 페이지를 찾을 수 없으므로 기본 설정 날짜로 대신합니다.");
            setCreatedDate("2025.05.27");
        }
    }, [pageId, setDomainName, setSystemName]);

    useEffect(() => {
        console.log("useEffect 실행 - location.state:", location.state);
        console.log("useEffect 실행 - conversionTime:", location.state?.conversionTime);
        // 중복 실행 방지
        if (loadedRef.current) return;
        if (location.state?.conversionTime) {
            console.log("conversionTime 설정:", location.state.conversionTime);
            setConversionTime(location.state.conversionTime);
        } else {
            console.log("conversionTime이 없음");
        }
        
        if (!pageId) {
            const savedPages = JSON.parse(localStorage.getItem("pages")) || [];
            if (savedPages.length > 0) {
                const fallbackPageId = savedPages[0].id;
                console.log("Fallback pageId로 리다이렉트:", fallbackPageId);
                navigate(`/dashboard/${fallbackPageId}`);
            } else {
                console.log("저장된 페이지가 없습니다");
            }
            return;
        }
        
        console.log("Dashboard 초기화 시작:", { pageId });
        setLoading(true);
        loadedRef.current = true;

        const loadAllData = async () => {
            try {
                await Promise.all([
                    loadEntities(pageId),
                    loadRelationships(pageId),
                    loadGraphData(pageId),
                    fetchSavedUrls(pageId),
                    loadDocumentsInfo(pageId, setUploadedDocs),
                    fetchGraphBuildStats(pageId, setGraphBuildStats),
                    fetchKnowledgeGraphStats(pageId, setKnowledgeGraphStats),
                ]);
                console.log("모든 데이터 로드 완료");
            } catch (error) {
                console.error("데이터 로드 중 오류:", error);
            } finally {
                setLoading(false);
            }
        };

        loadAllData();
        loadPageInfo();

        // Cleanup function
        return () => {
            loadedRef.current = false;
        };
    }, [pageId, navigate, loadEntities, loadRelationships, loadGraphData, fetchSavedUrls, loadPageInfo, location.state]);

    return (
        <div className={`dashboard-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
            <DashboardHeader isSidebarOpen={isSidebarOpen} />
            {/* 통계 섹션 */}
            <div className="stats-section">
                <div className="stats-grid">
                    <div className="stat-card date-card">
                        <div className="stat-header">
                            <span className="stat-icon">📅</span>
                        </div>
                        <div className="stat-number">{createdDate || ""}</div>
                        <div className="stat-label">생성된 날짜</div>
                    </div>
                    <div className="stat-card url-card">
                        <div className="stat-header">
                            <span className="stat-icon">🌐</span>
                            <span className="stat-change positive">+1</span>
                        </div>
                        <div className="stat-number">{urlCount}</div>
                        <div className="stat-label">등록된 URL</div>
                    </div>
                    
                    <div className="stat-card docs-card">
                        <div className="stat-header">
                            <span className="stat-icon">📄</span>
                            <span className="stat-change positive">+2</span>
                        </div>
                        <div className="stat-number">{docCount}</div>
                        <div className="stat-label">수집된 문서</div>
                    </div>
                    
                    <div className="stat-card entities-card">
                        <div className="stat-header">
                            <span className="stat-icon">🔗</span>
                            <span className="stat-change positive">+108</span>
                        </div>
                        <div className="stat-number">{filteredEntities.length}</div>
                        <div className="stat-label">추출된 엔티티</div>
                    </div>
                    
                    <div className="stat-card relations-card">
                        <div className="stat-header">
                            <span className="stat-icon">⚡</span>
                            <span className="stat-change positive">+105</span>
                        </div>
                        <div className="stat-number">{filteredRelationships.length}</div>
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

                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">🕷️</span>
                            <span className="stat-change positive">방금</span>
                        </div>
                        <div className="stat-number">2시간</div>
                        <div className="stat-label">크롤링에 걸린 시간</div>
                    </div>

                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">🧾</span>
                            <span className="stat-change positive">방금</span>
                        </div>
                        <div className="stat-number">3시간</div>
                        <div className="stat-label">url 전처리에 걸린 시간</div>
                    </div>

                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">📑</span>
                            <span className="stat-change positive">방금</span>
                        </div>
                        <div className="stat-number">{conversionTime || '1시간'}</div>
                        <div className="stat-label">문서 전처리에 걸린 시간</div>
                    </div>

                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">📍</span>
                            <span className="stat-change positive">방금</span>
                        </div>
                        <div className="stat-number">2시간</div>
                        <div className="stat-label">인덱싱에 걸린 시간</div>
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
                            <div className="search-controls">
                                <div className="search-box">
                                    <span className="search-icon">🔍</span>
                                    <input 
                                        type="text" 
                                        placeholder="URL에서 도메인으로 검색..."
                                    />
                                </div>
                                <div className="entity-count">
                                {`총 URL 수: ${urlCount}`}
                                </div>
                            </div>
                    </div>
                    
                    <div className="url-table-container">
                        <div className="table-scroll-wrapper">
                            <table className="url-table">
                                <thead>
                                    <tr>
                                        <th>URL</th>
                                        <th>카테고리</th>
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
                        <div className="search-controls">
                            <div className="search-box">
                                <span className="search-icon">🔍</span>
                                <input 
                                    type="text" 
                                    placeholder="문서명으로 검색..."
                                />
                            </div>
                            <div className="entity-count">
                                {`총 문서 수: ${docCount}`}
                            </div>
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
                                            activeTab === "entity" ? "title로 검색" : "엔티티나 관계로 검색..."
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
                                        : `총 관계 수: ${filteredRelationships.length}`}
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
                {/* 그래프 보기 섹션 수정 */}
                <div className="knowledge-graph-section">
                    <h1 className="section-title-with-icon">
                        <span className="icon">🕸️</span>
                        지식 그래프
                    </h1>
                    <div className="knowledge-graph-container">
                        {showGraph && graphData && !graphError ? (
                            <NetworkChart 
                                data={graphData} 
                                pageId={pageId}
                            />
                        ) : graphError ? (
                            <div className="graph-error-message">
                                그래프를 불러올 수 없습니다: {graphError}
                            </div>
                        ) : (
                            <div className="graph-loading-message">
                                그래프를 불러오는 중...
                            </div>
                        )}
                    </div>
                </div>
                {/* 통계 차트 섹션 */}
                <div className="stats-charts-section">
                    <div className="charts-container">
                        {/* 날짜별 데이터 수집 현황 */}
                        <div className="chart-card">
                            <div className="chart-header">
                                <h1 className="section-title-with-icon">
                                    <span className="chart-icon">📊</span>
                                    일별 데이터 수집 현황
                                </h1>
                            </div>
                            <div className="chart-content">
                                <div className="chart-legend">
                                    <div className="legend-item">
                                        <div className="legend-color url-color"></div>
                                        <span>URL</span>
                                    </div>
                                    <div className="legend-item">
                                        <div className="legend-color doc-color"></div>
                                        <span>문서</span>
                                    </div>
                                </div>
                                <div className="bar-chart">
                                    {dateStats.length > 0 ? (
                                        dateStats.map((item, index) => (
                                            <div key={index} className="bar-group">
                                                <div className="bars">
                                                    <div 
                                                        className="bar url-bar" 
                                                        style={{height: `${(item.url / maxValue) * 80}%`}}
                                                        title={`URL: ${item.url}개`}
                                                    ></div>
                                                    <div 
                                                        className="bar doc-bar" 
                                                        style={{height: `${(item.doc / maxValue) * 80}%`}}
                                                        title={`문서: ${item.doc}개`}
                                                    ></div>
                                                </div>
                                                <div className="bar-label">{item.date}일</div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="no-data-message">데이터가 없습니다</div>
                                    )}
                                </div>
                                <div className="chart-stats">
                                    <div className="stat-item">
                                        <span className="stat-label">총 URL</span>
                                        <span className="stat-value">{urlCount}개</span>
                                    </div>
                                    <div className="stat-item">
                                        <span className="stat-label">총 문서</span>
                                        <span className="stat-value">{docCount}개</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* 지식그래프 구축 현황 */}
                        <div className="chart-card">
                            <div className="chart-header">
                                <h1 className="section-title-with-icon">
                                    <span className="chart-icon">📈</span>
                                    일별 지식그래프 구축 현황
                                </h1>
                            </div>
                            <div className="chart-content">
                                <div className="chart-legend">
                                    <div className="legend-item">
                                        <div className="legend-color entity-color"></div>
                                        <span>엔티티</span>
                                    </div>
                                    <div className="legend-item">
                                        <div className="legend-color relationship-color"></div>
                                        <span>관계</span>
                                    </div>
                                </div>
                                <div className="bar-chart">
                                    {knowledgeGraphDateStats.length > 0 ? (
                                        knowledgeGraphDateStats.map((item, index) => (
                                            <div key={index} className="bar-group">
                                                <div className="bars">
                                                    <div 
                                                        className="bar entity-bar" 
                                                        style={{height: `${(item.entity / knowledgeGraphMaxValue) * 80}%`}}
                                                        title={`엔티티: ${item.entity}개`}
                                                    ></div>
                                                    <div 
                                                        className="bar relationship-bar" 
                                                        style={{height: `${(item.relationship / knowledgeGraphMaxValue) * 80}%`}}
                                                        title={`관계: ${item.relationship}개`}
                                                    ></div>
                                                </div>
                                                <div className="bar-label">{item.date}일</div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="no-data-message">데이터가 없습니다</div>
                                    )}
                                </div>
                                <div className="chart-stats">
                                    <div className="stat-item">
                                        <span className="stat-label">총 엔티티</span>
                                        <span className="stat-value">{entities.length}개</span>
                                    </div>
                                    <div className="stat-item">
                                        <span className="stat-label">총 관계</span>
                                        <span className="stat-value">{relationships.length}개</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DashboardPage;