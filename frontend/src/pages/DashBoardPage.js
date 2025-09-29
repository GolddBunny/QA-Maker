import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';

import "../styles/DashBoardPage.css";
import NetworkChart from "../components/charts/NetworkChart";
import { usePageContext } from '../utils/PageContext';
import { fetchEntities, fetchRelationships } from '../api/AllParquetView';
import { fetchGraphData } from '../api/AdminGraph';
import { EntityTable, RelationshipTable } from '../components/hooks/ResultTables';
import { fetchSavedUrls as fetchSavedUrlsApi } from '../api/UrlApi';
import { loadUploadedDocsFromFirestore } from '../api/UploadedDocsFromFirestore';
import { loadStepExecutionTimes } from '../services/LoadStepExecutionTimes';
import { db } from "../firebase/sdk";

import { 
    fetchKnowledgeGraphStats 
} from '../components/dashboard/dashboardDataLoaders';

import { 
    getDateStats, 
    getKnowledgeGraphDateStats, 
    getGraphBuildDateStats 
} from '../components/dashboard/dashboardStats';
import { doc, getDoc, collection, query, where, orderBy, onSnapshot } from "firebase/firestore";

const DashboardPage = () => {
    const navigate = useNavigate();
    const { pageId } = useParams();
    const { currentPageId, domainName, setDomainName, systemName, setSystemName } = usePageContext();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [activeTab, setActiveTab] = useState("entity");
    const [showGraph, setShowGraph] = useState(true);
    const [loading, setLoading] = useState(true);
    const [entitySearchTerm, setEntitySearchTerm] = useState("");
    const [relationshipSearchTerm, setRelationshipSearchTerm] = useState("");
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
    const { getCurrentPageSysName } = usePageContext();
    const [urlCount, setUrlCount] = useState(0);
    const [docCount, setDocCount] = useState(0);

    const [stepExecutionTimes, setStepExecutionTimes] = useState({
        crawling: null,
        structuring: null,
        document: null,
        indexing: null,
    });

    // 초 -> 분/초 문자열로 변환
    const formatSecondsToMinutes = (seconds) => {
        if (seconds == null) return "정보 없음";
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}분 ${secs}초`;
    };

    const DashboardHeader = ({ isSidebarOpen, toggleSidebar }) => {
        return (
            <header className="dashboard-header">
                <div className="dashboard-header-content">
                    <div className="dashboard-header-left">
                        {/* 관리자 페이지로 돌아가기 버튼 */}
                        <button 
                            className="back-button"
                            onClick={() => navigate(`/admin/${pageId}`)}
                            title="관리자 페이지로 돌아가기"
                        >
                            ← 돌아가기
                        </button>
                        <div className="dashboard-logo-section">
                        <h1 className="dashboard-title">
                            {systemName && `${systemName} `}Log Analyzer
                        </h1>
                    </div>
                    </div>
                </div>
            </header>
        );
    };

    // 엔티티 데이터 로드
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

    // 관계 데이터 로드
    const loadRelationships = useCallback(async (id) => {
        if (!id) return;
        
        try {
            console.log("관계 데이터 로드 중...");
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

    // 그래프 데이터 로드
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

    // // 저장된 URL 가져오기
    // const fetchSavedUrls = useCallback(async (pageId) => {
    //   const urls = await fetchSavedUrlsApi(pageId);
    //   const urlArray = Array.isArray(urls) ? urls : [];
    //   setUploadedUrls(urlArray); // undefined 방지
    //   setUrlCount(urlArray.length);
    // } , []);

    // // 저장된 문서 목록 가져오기
    // const fetchDocuments = useCallback(async (pageId) => {
    //     if (!pageId) return;
        
    //     try {
    //         console.log("문서 목록 로드 중...");
    //         const { docs: documentsData, count: documentCount } = await loadUploadedDocsFromFirestore(pageId);
            
    //         // 문서 목록과 개수 모두 설정
    //         setUploadedDocs(documentsData || []);
    //         setDocCount(documentCount || 0);
            
    //         console.log("문서 목록 로드 완료:", {
    //             count: documentCount,
    //             docs: documentsData?.length || 0
    //         });
    //     } catch (error) {
    //         console.error("문서 목록 가져오기 중 오류:", error);
    //         setUploadedDocs([]);
    //         setDocCount(0);
    //     }
    // }, []);

    // 통계 데이터 계산
    const dateStats = useMemo(() => {
        return getDateStats(uploadedUrls, uploadedDocs);
    }, [uploadedUrls, uploadedDocs]);

    const knowledgeGraphDateStats = useMemo(() => 
        getKnowledgeGraphDateStats(
            knowledgeGraphStats, 
            createdDate,
            entities.length, 
            relationships.length
        ), 
        [knowledgeGraphStats, createdDate, entities.length, relationships.length]
    );

    const graphDateStats = useMemo(() => 
        getGraphBuildDateStats(
            graphBuildStats, 
            createdDate,
            entities.length, 
            relationships.length
        ), 
        [graphBuildStats, createdDate, entities.length, relationships.length]
    );

    // 통계 차트용 최대값 계산
    const maxValue = Math.max(...dateStats.map(item => Math.max(item.url, item.doc)), 1);
    const knowledgeGraphMaxValue = Math.max(
        ...knowledgeGraphDateStats.map(item => Math.max(item.entity, item.relationship)), 
        1
    );
    const maxGraphValue = Math.max(...graphDateStats.map(item => Math.max(item.entity, item.relationship)), 1);

    // 엔티티 검색 필터링
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
            
        console.log("엔티티 필터링 완료:", {
            filteredCount: filtered.length,
            removedCount: entities.length - filtered.length,
        });
        
        return filtered;
    }, [entities, entitySearchTerm]);

    // 관계 검색 필터링
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
            
        console.log("관계 필터링 완료:", {
            filteredCount: filtered.length,
            removedCount: relationships.length - filtered.length,
        });
        
        return filtered;
    }, [relationships, relationshipSearchTerm]);

    // 페이지 정보 로드 (LocalStorage 기반)
    // const loadPageInfo = useCallback(() => {
    //     const pages = JSON.parse(localStorage.getItem('pages')) || [];
        
    //     // 디버깅 로그
    //     console.log("찾는 pageId:", pageId, typeof pageId);
    //     console.log("저장된 페이지들:", pages.map(p => ({ id: p.id, type: typeof p.id, name: p.name })));
        
    //     // 정확히 일치하는지 확인
    //     let currentPage = pages.find(page => page.id === pageId);
        
    //     // 타입 불일치 -> 문자열/숫자 변환해서 재시도
    //     if (!currentPage) {
    //         currentPage = pages.find(page => 
    //             String(page.id) === String(pageId)
    //         );
    //         console.log("타입 변환 후 찾은 페이지:", currentPage);
    //     }
        
    //     console.log("최종 현재 페이지 정보:", currentPage);
        
    //     if (currentPage) {
    //         setDomainName(currentPage.name || "");
    //         setSystemName(currentPage.sysname || "");
            
    //         if (currentPage.createdAt) {
    //             try {
    //                 const date = new Date(currentPage.createdAt);
    //                 const year = date.getFullYear();
    //                 const month = String(date.getMonth() + 1).padStart(2, '0');
    //                 const day = String(date.getDate()).padStart(2, '0');
    //                 setCreatedDate(`${year}.${month}.${day}`);
    //             } catch (error) {
    //                 console.log('날짜 파싱 실패:', error);
    //                 setCreatedDate("정보없음");
    //             }
    //         } else {
    //             setCreatedDate("정보없음");
    //         }
    //     } else {
    //         console.warn("페이지를 찾을 수 없습니다:", pageId);
    //         setCreatedDate("정보없음");
    //     }
    // }, [pageId, setDomainName, setSystemName]);

    // Firebase에서 페이지 정보 로드
    const loadPageInfo = useCallback(async () => {
        try {
            console.log("Firebase에서 페이지 정보 로드 시작, pageId:", pageId);
            
            // Firestore에서 페이지 문서 가져오기
            const pageDocRef = doc(db, 'pages', pageId);
            const pageDoc = await getDoc(pageDocRef);
            
            if (pageDoc.exists()) {
                const pageData = pageDoc.data();
                console.log("Firebase에서 가져온 페이지 데이터:", pageData);
                
                // 도메인명과 시스템명 설정
                setDomainName(pageData.name || "");
                setSystemName(pageData.sysname || "");
                
                // createdAt 날짜 처리
                if (pageData.createdAt) {
                    try {
                        let date;
                        
                        // Firestore Timestamp 객체인지 확인
                        if (pageData.createdAt.toDate && typeof pageData.createdAt.toDate === 'function') {
                            // Firestore Timestamp인 경우
                            date = pageData.createdAt.toDate();
                            console.log("Firestore Timestamp에서 변환된 날짜:", date);
                        } else if (typeof pageData.createdAt === 'string') {
                            // 문자열 형태의 날짜인 경우 (ISO 8601 형식 등)
                            date = new Date(pageData.createdAt);
                            console.log("문자열에서 변환된 날짜:", date);
                        } else {
                            // 그 외의 경우 직접 Date 객체로 변환 시도
                            date = new Date(pageData.createdAt);
                            console.log("기타 형태에서 변환된 날짜:", date);
                        }
                        
                        // 날짜가 유효한지 확인
                        if (date && !isNaN(date.getTime())) {
                            const year = date.getFullYear();
                            const month = String(date.getMonth() + 1).padStart(2, '0');
                            const day = String(date.getDate()).padStart(2, '0');
                            const formattedDate = `${year}.${month}.${day}`;
                            
                            console.log("최종 포맷된 날짜:", formattedDate);
                            setCreatedDate(formattedDate);
                        } else {
                            console.error("유효하지 않은 날짜:", pageData.createdAt);
                            setCreatedDate("날짜 형식 오류");
                        }
                        
                    } catch (dateError) {
                        console.error("날짜 파싱 실패:", dateError, "원본 데이터:", pageData.createdAt);
                        setCreatedDate("날짜 파싱 실패");
                    }
                } else {
                    console.warn("createdAt 필드가 없습니다:", pageData);
                    setCreatedDate("생성일 없음");
                }
                
            } else {
                console.warn("해당 페이지 문서가 존재하지 않습니다:", pageId);
                setDomainName("");
                setSystemName("");
                setCreatedDate("페이지 없음");
            }
            
        } catch (error) {
            console.error("Firebase에서 페이지 정보 로드 실패:", error);
            setCreatedDate("로드 실패");
        }
    }, [pageId, setDomainName, setSystemName]);

    // 초기 데이터 로드 및 Firestore 실시간 구독
    useEffect(() => {
        if (loadedRef.current) return;
        
        if (location.state?.conversionTime) {
            console.log("conversionTime 설정:", location.state.conversionTime);
            setConversionTime(location.state.conversionTime);
        }
        
        if (!pageId) {
            const savedPages = JSON.parse(localStorage.getItem("pages")) || [];
            if (savedPages.length > 0) {
                const fallbackPageId = savedPages[0].id;
                console.log("Fallback pageId로 리다이렉트:", fallbackPageId);
                navigate(`/dashboard/${fallbackPageId}`);
            }
            return;
        }

        console.log("Dashboard 초기화 시작:", { pageId });
        setLoading(true);
        loadedRef.current = true;

        // 1. Firestore URL 실시간 구독
        const urlsRef = collection(db, "url_list", pageId, "list");
        const urlQuery = query(urlsRef, orderBy("date", "desc"));
        const unsubscribeUrls = onSnapshot(urlQuery, (snapshot) => {
            const urlArray = snapshot.docs.map(doc => doc.data());
            console.log("URL 실시간 업데이트:", urlArray.length);
            setUploadedUrls(urlArray);
            setUrlCount(urlArray.length);
        }, (error) => {
            console.error("URL Firestore 구독 에러:", error);
        });

        // 2. Firestore Document 실시간 구독
        const docsRef = collection(db, "document_files");
        const docQuery = query(
            docsRef, 
            where("page_id", "==", pageId),
            orderBy("date", "desc")
        );

        const unsubscribeDocs = onSnapshot(docQuery, (snapshot) => {
            const docArray = snapshot.docs.map(doc => doc.data());
            console.log("문서 실시간 업데이트:", docArray.length);
            setUploadedDocs(docArray);
            setDocCount(docArray.length);
        }, (error) => {
            console.error("문서 Firestore 구독 에러:", error);
        });

        // 3. 초기 데이터 로드
        const init = async () => {
            try {
                // Firebase에서 stepExecutionTimes 불러오기
                const times = await loadStepExecutionTimes(pageId);
                console.log("Firebase로부터 stepExecutionTimes 로딩:", times);
                setStepExecutionTimes(times);

                // 나머지 데이터 병렬 로드
                await Promise.all([
                    loadEntities(pageId),
                    loadRelationships(pageId),
                    loadGraphData(pageId),
                    fetchKnowledgeGraphStats(pageId, setKnowledgeGraphStats),
                    loadPageInfo()
                ]);
                console.log("모든 데이터 로드 완료");
            } catch (error) {
                console.error("데이터 로드 중 오류:", error);
            } finally {
                setLoading(false);
            }
        };

        init();

        // Cleanup function
        return () => {
            console.log("Dashboard cleanup - 구독 해제");
            unsubscribeUrls();
            unsubscribeDocs();
            loadedRef.current = false;
        };
    }, [pageId, navigate, loadEntities, loadRelationships, loadGraphData, loadPageInfo, location.state]);

    return (
        <div className={`dashboard-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
            {/* 헤더 */}
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
                            {/* <span className="stat-change positive">+1</span> */}
                        </div>
                        <div className="stat-number">{urlCount}</div>
                        <div className="stat-label">등록된 URL</div>
                    </div>
                    
                    <div className="stat-card docs-card">
                        <div className="stat-header">
                            <span className="stat-icon">📄</span>
                        </div>
                        <div className="stat-number">{docCount}</div>
                        <div className="stat-label">수집된 문서</div>
                    </div>
                    
                    <div className="stat-card entities-card">
                        <div className="stat-header">
                            <span className="stat-icon">🔗</span>
                        </div>
                        <div className="stat-number">{filteredEntities.length}</div>
                        <div className="stat-label">추출된 엔티티</div>
                    </div>
                    
                    <div className="stat-card relations-card">
                        <div className="stat-header">
                            <span className="stat-icon">⚡</span>
                        </div>
                        <div className="stat-number">{filteredRelationships.length}</div>
                        <div className="stat-label">구축된 관계</div>
                    </div>
                    
                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">⏰</span>
                        </div>
                        <div className="stat-number">2시간 전</div>
                        <div className="stat-label">마지막 업데이트</div>
                    </div>

                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">🕷️</span>
                        </div>
                        <div className="stat-number">{formatSecondsToMinutes(stepExecutionTimes.crawling)}</div>
                        <div className="stat-label">크롤링에 걸린 시간</div>
                    </div>

                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">🧾</span>
                        </div>
                        <div className="stat-number">{formatSecondsToMinutes(stepExecutionTimes.structuring)}</div>
                        <div className="stat-label">url 전처리에 걸린 시간</div>
                    </div>

                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">📑</span>
                        </div>
                        <div className="stat-number">{formatSecondsToMinutes(stepExecutionTimes.document)}</div>
                        <div className="stat-label">문서 전처리에 걸린 시간</div>
                    </div>

                    <div className="stat-card time-card">
                        <div className="stat-header">
                            <span className="stat-icon">📍</span>
                        </div>
                        <div className="stat-number">{formatSecondsToMinutes(stepExecutionTimes.indexing)}</div>
                        <div className="stat-label">인덱싱에 걸린 시간</div>
                    </div>
                </div>
            </div>
            <hr style={{ margin: "2rem 0", borderTop: "1px solid #ccc" }} />
            <div className={`dashboard-content ${isSidebarOpen ? 'sidebar-open' : ''}`}>
                {/* URL 리스트 섹션 */}
                <div className="url-list-section">
                    <div className="section-header">
                        <h2 className="section-title-with-icon">
                            <span className="icon">🌐</span>
                            URL 리스트
                        </h2>
                            <div className="search-controls">
                                {/* <div className="search-box">
                                    <span className="search-icon">🔍</span>
                                    <input 
                                        type="text" 
                                        placeholder="URL에서 도메인으로 검색..."
                                    />
                                </div> */}
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
                            {/* <div className="search-box">
                                <span className="search-icon">🔍</span>
                                <input 
                                    type="text" 
                                    placeholder="문서명으로 검색..."
                                />
                            </div> */}
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

                {/* QA 시스템 정보 보기 섹션 */}
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
                        지식그래프 네트워크 시각화 (Top 200 엔티티)
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
                                                        data-count={item.url}
                                                    >
                                                        <span className="bar-tooltip">URL: {item.url}개</span>
                                                    </div>
                                                    <div 
                                                        className="bar doc-bar" 
                                                        style={{height: `${(item.doc / maxValue) * 80}%`}}
                                                        title={`문서: ${item.doc}개`}
                                                        data-count={item.doc}
                                                    >
                                                        <span className="bar-tooltip">문서: {item.doc}개</span>
                                                    </div>
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
                                                        data-count={item.entity}
                                                    >
                                                        <span className="bar-tooltip">엔티티: {item.entity}개</span>
                                                    </div>
                                                    <div 
                                                        className="bar relationship-bar" 
                                                        style={{height: `${(item.relationship / knowledgeGraphMaxValue) * 80}%`}}
                                                        title={`관계: ${item.relationship}개`}
                                                        data-count={item.relationship}
                                                    >
                                                        <span className="bar-tooltip">관계: {item.relationship}개</span>
                                                    </div>
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