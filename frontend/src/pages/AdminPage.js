import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import "../styles/AdminPage.css";
import SidebarAdmin from "../components/navigation/SidebarAdmin";
import NetworkChart from "../components/charts/NetworkChart";
import { getCurrentPageId, getPages, savePages } from '../utils/storage'; // 유틸리티 함수 임포트
import { usePageContext } from '../utils/PageContext';
import { useQAHistoryContext } from '../utils/QAHistoryContext'; // QA History Context 추가
import { FileDropHandler } from '../api/handleFileDrop';
import { fetchEntities, fetchRelationships } from '../api/AllParquetView';
import { fetchGraphData } from '../api/AdminGraph';
import { EntityTable, RelationshipTable } from '../components/hooks/ResultTables';
import { fetchSavedUrls as fetchSavedUrlsApi, uploadUrl } from '../api/UrlApi';
import { checkOutputFolder as checkOutputFolderApi } from '../api/HasOutput';
import { processDocuments, loadUploadedDocs } from '../api/DocumentApi';
import { applyIndexing, updateIndexing } from '../api/IndexingButton';
import AdminHeader from '../services/AdminHeader';
import "../styles/AdminPage.css";
import ProgressingBar from '../services/ProgressingBar';

const BASE_URL = 'http://localhost:5000';
const UPLOAD_URL = `${BASE_URL}/upload-documents`;
const PROCESS_URL = `${BASE_URL}/process-documents`;
const UPDATE_URL = `${BASE_URL}/update`;
const APPLY_URL = `${BASE_URL}/apply`;
const URL_URL = `${BASE_URL}`;


const AdminPage = () => {
    const navigate = useNavigate();
    const { pageId } = useParams();  // URL에서 페이지 ID 가져오기
    const [urlInput, setUrlInput] = useState("");
    const [uploadedUrls, setUploadedUrls] = useState([]);
    //const [uploadedDocs, setUploadedDocs] = useState([]);
    //const [currentPageId, setCurrentPageId] = useState(null);
    const [isNewPage, setIsNewPage] = useState(false);
    const [isUrlLoading, setIsUrlLoading] = useState(false);
    const [isFileLoading, setIsFileLoading] = useState(false);
    const [isProcessLoading, setIsProcessLoading] = useState(false);
    const [isApplyLoading, setIsApplyLoading] = useState(false);
    const [hasDocuments, setHasDocuments] = useState(false);
    const fileInputRef = useRef(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [duplicateFileName, setDuplicateFileName] = useState(null); //중복 파일 검사

    const [activeTab, setActiveTab] = useState("entity"); //최종 결과물 활성화된 버튼 
    const [entities, setEntities] = useState([]);
    const [relationships, setRelationships] = useState([]);
    const [entitySearchTerm, setEntitySearchTerm] = useState("");
    const [relationshipSearchTerm, setRelationshipSearchTerm] = useState("");
    const [isSearchHovered, setIsSearchHovered] = useState(false);
    const [graphData, setGraphData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [graphError, setGraphError] = useState(null);
    const [dataFetchError, setDataFetchError] = useState(null);
    const [showGraph, setShowGraph] = useState(false);
    const graphDataCacheRef = useRef({});
    const { currentPageId, updatePages, updatePageSysName, updatePageName,
      systemName, setSystemName, domainName, setDomainName
     } = usePageContext();
    const [uploadedDocs, setUploadedDocs] = useState([]); // 초기값은 빈 배열
    // Firebase QA History Context 사용 (pageId 기반, Firebase 사용)
    const { 
        qaHistory, 
        loading: qaLoading, 
        error: qaError 
    } = useQAHistoryContext(pageId, true); // useFirestore = true로 설정
    // 작업 처리 중인지 확인 상태
    const isAnyProcessing = isUrlLoading || isFileLoading || isProcessLoading || isApplyLoading;
    const [hasOutput, setHasOutput] = useState(null);
    const [isCheckingOutput, setIsCheckingOutput] = useState(false);

    const { handleFileDrop } = FileDropHandler({
      uploadedDocs,
      setUploadedDocs,
      setDuplicateFileName,
      setIsFileLoading,
      setHasDocuments,
      isAnyProcessing,
      pageId
    });

    // URL 목록 불러오기
    const fetchSavedUrls = useCallback(async (pageId) => {
      const urls = await fetchSavedUrlsApi(pageId);
      setUploadedUrls(urls);
    }, []);

    // 문서 정보 로드
    const loadDocumentsInfo = useCallback(async (id) => {
      if (!id) return;
      
      try {
        const res = await fetch(`${BASE_URL}/documents/${id}`);  // 문서 목록 api
        const data = await res.json();

        if (data.success) {
          const uploaded = data.uploaded_files;
          setUploadedDocs(uploaded);
          setHasDocuments(uploaded.length > 0);
          setIsNewPage(uploaded.length === 0);
        } else {
          console.error("문서 목록 로드 실패:", data.error);
        }
      } catch (error) {
        console.error("문서 정보 로드 실패:", error);
      }
    }, []);

    // Output 폴더 확인
    const checkOutputFolder = useCallback(async (pageId) => {
      if (!pageId) return;
      
      setIsCheckingOutput(true);
      try {
        const hasOutputResult = await checkOutputFolderApi(pageId);
        setHasOutput(hasOutputResult); // true/false/null
      } catch (error) {
        console.error("Output 폴더 확인 중 오류:", error);
        setHasOutput(null);
      } finally {
        setIsCheckingOutput(false);
      }
    }, []);

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
          navigate(`/admin/${fallbackPageId}`);
        }
        return;
      }
      
      console.log("현재 admin pageId:", pageId);

      // 페이지가 변경될 때마다 상태 초기화
      setEntities([]);
      setRelationships([]);
      setGraphData(null);
      setUploadedUrls([]);
      setUploadedDocs([]);
      setHasDocuments(false);
      setHasOutput(null);

      loadUploadedDocs(pageId)
        .then(docs => setUploadedDocs(docs))
        .catch(error => {
          console.error("문서 목록 로드 중 오류:", error);
          setUploadedDocs([]);
        });

      // 페이지 ID가 유효한 경우에만 데이터 로드
      if (pageId) {
        // 병렬로 데이터 로드 작업 실행
        Promise.all([
          loadDocumentsInfo(pageId),
          fetchSavedUrls(pageId),
          checkOutputFolder(pageId),
          loadAllData(pageId),
          fetchGraphData({
            pageId: pageId,
            graphDataCacheRef,
            setGraphData
          }),
        ]).catch(error => {
          console.error("데이터 로드 중 오류:", error);
        });
        
        const pages = JSON.parse(localStorage.getItem('pages')) || [];
        const currentPage = pages.find(page => page.id === pageId);
        if (currentPage) {
          setDomainName(currentPage.name || "");
          setSystemName(currentPage.sysname || "");
        }
      }
    }, [pageId, navigate, loadDocumentsInfo, fetchSavedUrls, checkOutputFolder, loadAllData]);

    const toggleSidebar = () => {
      setIsSidebarOpen(!isSidebarOpen);
    };
    
    const handleDragOver = (e) => {
      if (isAnyProcessing) return;

      e.preventDefault();
      setIsDragOver(true);
    };

    const handleDragLeave = () => {
      if (isAnyProcessing) return;

      setIsDragOver(false);
    };
    
    // URL 유효성 검사
    const isValidUrl = (url) => {
      try {
        new URL(url);
        return true;
      } catch (error) {
        return false;
      }
    };
    
    // URL 저장
    const handleUrlUpload = async () => {
      if (urlInput.trim() === '') return;
      if (isAnyProcessing) return;

      if (!isValidUrl(urlInput)) {
        alert('유효한 URL을 입력해주세요');
        return;
      }

      setIsUrlLoading(true);

      try {
        console.log("pageId: ", pageId);
        const result = await uploadUrl(pageId, urlInput);

        if (result.success) {
          console.log('URL 저장 완료:', result.urls);
          setUploadedUrls(result.urls || []);
          setUrlInput('');
          alert("URL이 등록되었습니다.");
        } else {
          throw new Error('URL 저장 실패: ' + result.error);
        }
      } catch (error) {
        console.error('URL 추가 오류:', error);
        alert('오류 발생: ' + error.message);
      } finally {
        setIsUrlLoading(false);
      }
    };

    // 문서 처리 함수
    const handleProcessDocuments = async () => {
      if (!pageId) {
        alert("먼저 페이지를 생성해주세요.");
        return;
      }
      if (uploadedDocs.length === 0) {
        alert("먼저 문서를 업로드해주세요.");
        return;
      }

      if (isAnyProcessing) return;

      setIsProcessLoading(true);

      try {
        const result = await processDocuments(pageId);

        if (result.success) {
          alert("문서 처리 완료");
        } else {
          console.error("문서 처리 실패:", result.error);
          alert("문서 처리에 실패했습니다.");
        }
      } catch (error) {
        console.error("문서 처리 중 오류:", error);
        alert("문서 처리 중 오류가 발생했습니다.");
      } finally {
        setIsProcessLoading(false);
      }
    };

    // 인덱싱 버튼
    const handleApply = async () => {
      if (!pageId) {
        alert("먼저 페이지를 생성해주세요.");
        return;
      }
      if (uploadedDocs.length === 0 && uploadedUrls.length === 0) {
        alert("먼저 문서나 URL을 업로드해주세요.");
        return;
      }

      if (isAnyProcessing) return;

      setIsApplyLoading(true);

      try {
        const result = await applyIndexing(pageId);
        if (result.success) {
          alert("문서 인덱싱 완료");
          setIsNewPage(false);

          // 인덱싱 완료 후 데이터 다시 로드
          await Promise.all([
            loadAllData(pageId),
            fetchSavedUrls(pageId).then(setUploadedUrls),
            loadDocumentsInfo(pageId),
            checkOutputFolder(pageId),
            fetchGraphData({
              pageId,
              graphDataCacheRef,
              setGraphData,
            })
          ]);
        } else {
          alert(`문서 인덱싱 실패: ${result.error}`);
        }
      } finally {
        setIsApplyLoading(false);
      }
    };

    const handleUpdate = async () => {
      if (uploadedDocs.length === 0 && uploadedUrls.length === 0) {
        alert("먼저 문서나 URL을 업로드해주세요.");
        return;
      }

      if (isAnyProcessing) return;

      setIsApplyLoading(true);

      try {
        const result = await updateIndexing(pageId);
        if (result.success) {
          alert("업데이트 완료");

          // 업데이트 완료 후 데이터 다시 로드
          await Promise.all([
            loadAllData(pageId),
            fetchSavedUrls(pageId).then(setUploadedUrls),
            loadDocumentsInfo(pageId),
            checkOutputFolder(pageId),
            fetchGraphData({
              pageId,
              graphDataCacheRef,
              setGraphData,
            })
          ]);
        } else {
          alert(`업데이트 실패: ${result.error}`);
        }
      } finally {
        setIsApplyLoading(false);
      }
    };

    const sortedDocs = [...uploadedDocs].sort((a, b) => {
  const dateA = new Date(a.date);
  const dateB = new Date(b.date);
  
  if (dateA.getTime() === dateB.getTime()) {
    return a.original_filename.localeCompare(b.original_filename);
  }

  return dateB - dateA; // 최근 날짜가 먼저 오도록 (내림차순)
});

    const filteredEntities = (entities || [])
      .filter((item) =>
        item.title && item.title.toLowerCase().includes(entitySearchTerm.toLowerCase())
      )
      .sort((a, b) => a.id - b.id);

    const filteredRelationships = (relationships|| [])
      .filter(
        (item) =>
          item.description &&
          item.description.toLowerCase().includes(relationshipSearchTerm.toLowerCase())
      )
      .sort((a, b) => a.id - b.id);

    const handleShowGraph = () => {
      if (!showGraph) {
        // 그래프를 처음 여는 경우에만 fetch
        if (!graphData && pageId) {
          fetchGraphData({
            pageId: pageId,
            graphDataCacheRef,
            setGraphData
          });
        }
      }
      setShowGraph(prev => !prev);
    };
    
    const handleAnalyzer = async () => {
      if (!pageId) {
        alert("먼저 페이지를 생성해주세요.");
        return;
      }

      if (isAnyProcessing) return;

      // Analyzer 로직 구현
      try {
        // 여기에 analyzer 관련 API 호출 또는 동작 구현
        console.log("Analyzer 실행");
        // 예: const result = await runAnalyzer(pageId);
        alert("Analyzer 실행 완료");
      } catch (error) {
        console.error("Analyzer 실행 중 오류:", error);
        alert("Analyzer 실행 중 오류가 발생했습니다.");
      }
    };

    return (
      <div className={`admin-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
        <AdminHeader isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />

        {/* 사이드바는 AdminPage 안에서만 조건부 렌더링 */}
        {isSidebarOpen && (
          <SidebarAdmin
            isSidebarOpen={isSidebarOpen}
            toggleSidebar={toggleSidebar}
          />
        )}

        <div className={`admin-content ${isSidebarOpen ? 'sidebar-open' : ''}`}>
          {/* 상단 입력부 */}
          <div className="input-container" id="name">
          <div className="input-row-horizontal">
            <div className="input-field">
              <input
                type="text"
                placeholder="도메인 이름을 정해주세요"
                value={domainName}
                onChange={(e) => {
                  const newName = e.target.value;
                  setDomainName(newName);
                  updatePageName(pageId, newName);
                }}
              />
            </div>

            <div className="input-field">
              <input
                type="text"
                placeholder="QA 시스템 이름을 정해주세요"
                value={systemName}
                onChange={(e) => setSystemName(e.target.value)}
              />
            </div>

            <button
              className="apply-button-admin"
              onClick={() => {
                updatePageName(pageId, domainName);
                updatePageSysName(pageId, systemName);
              }}
            >
              적용
            </button>
          </div>
        </div>
      
        <div className="upload-section-wrapper" id="register">
          {/* 왼쪽 URL 섹션 */}
          <div className="url-upload">
            <h2 className="section-title">URL 등록</h2>
            <p className="section-desc">URL을 등록하면 하위 페이지까지 모두 가져옵니다.</p>
            {/* URL 입력란 및 버튼 */}
            <div className="url-input">
              <input
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder={isAnyProcessing ? '' : 'https://example.com'}
                className="url-input-field"
                disabled={isAnyProcessing}
                style={{ color: isAnyProcessing ? 'transparent' : 'inherit' }}
              />

              {/* 버튼은 로딩 중일 때 숨김 */}
              {!isAnyProcessing && (
                <button
                  onClick={handleUrlUpload}
                  disabled={isAnyProcessing}
                  className="upload-button"
                >
                  +
                </button>
              )}
              </div>

              <table className="upload-table">
                <thead>
                  <tr>
                    <th>URL</th>
                    <th>업로드 날짜</th>
                  </tr>
                </thead>
              </table>
              <div className="upload-table-wrapper">
                <table className="upload-table">
                <tbody>
                  {uploadedUrls.length > 0 ? (
                    uploadedUrls.map((item, idx) => (
                      <tr key={idx}>
                        <td>{item.url}</td>
                        <td>{item.date}</td>
                      </tr>
                    ))
                  ) : (
                          <div className="no-message">
                            업로드된 문서가 없습니다.<br />
                            url을 등록해주세요.
                          </div>
                        )}
                </tbody>
              </table>
            </div>
          </div>
          
          {/* 오른쪽 문서 섹션 */}
          <div className="doc-upload">
            <h2 className="section-title">문서 등록</h2>
            <div className="upload-container">
              <div
                className={`doc-dropzone ${isDragOver ? 'drag-over' : ''} ${isAnyProcessing ? 'zone-disabled' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleFileDrop}
                onClick={() => !isAnyProcessing && fileInputRef.current.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  multiple
                  accept=".pdf, .txt, .hwp, .docx"
                  onChange={handleFileDrop}
                  disabled={isAnyProcessing}
                />
                
                {/* 기존 텍스트는 isAnyProcessing이 false일 때만 보이도록 */}
                {!isAnyProcessing && (
                  <>
                    <p>
                      {isFileLoading
                        ? '처리 중...'
                        : isDragOver
                        ? '여기에 문서를 놓으세요'
                        : '문서를 여기로 드래그하거나 클릭하여 업로드하세요'}
                    </p>
                    <p className="file-support-text">PDF, DOCX, TXT, HWP 문서 지원</p>
                  </>
                )}
              </div>
              {!isAnyProcessing && (
                <button
                  onClick={handleProcessDocuments}
                  disabled={isAnyProcessing}
                  className="process-button"
                >
                  +
                </button>
              )}
            </div>

            <table className="document-table">
              <thead>
                <tr>
                  <th>문서 이름</th>
                  <th>카테고리</th>
                  <th>업로드 날짜</th>
                </tr>
              </thead>
              </table>
                <div className="document-table-scroll">
                  <table className="document-table">
                    <tbody>
                      {uploadedDocs.length > 0 ? (
                        
                        sortedDocs.map((doc, index) => (
                          <tr key={index}>
                            <td>{doc.original_filename}</td>
                            <td><span className="category-pill">{doc.category}</span></td>
                            <td>{doc.date}</td>
                          </tr>
                        ))
                      ) : (
                          <div className="no-message">
                            업로드된 문서가 없습니다.<br />
                            문서를 등록해주세요.
                          </div>
                        )}
                    </tbody>
                  </table>
                </div>
            {duplicateFileName && (
              <div className="duplicate-warning-box">
                <div className="duplicate-warning-message">
                  <strong>중복된 문서</strong><br />
                  <span>{duplicateFileName}은 이미 등록된 문서입니다. 문서명을 변경해주세요.</span>
                </div>
                <button
                  className="close-warning-button"
                  onClick={() => setDuplicateFileName(null)}
                >
                  ×
                </button>
              </div>
            )}
          </div>
        </div>
        {/* 적용 버튼 */}
      <div className="apply-btn-row">
          {isAnyProcessing ? (
            <ProgressingBar />
          ) : hasOutput ? (
            // QA System이 구축된 후 - 두 개 버튼을 가로 정렬로 표시
            <>
              <button 
                className="btn-apply-update"
                onClick={handleUpdate}
                disabled={isCheckingOutput}
              > 
                Update QA System
              </button>
              <button 
                className="btn-apply-update"
                onClick={handleAnalyzer} // 이 함수를 구현해야 함
                disabled={isCheckingOutput}
              > 
                Analyzer
              </button>
            </>
          ) : (
            // 처음 상태 - Build QA System 버튼만 표시
            <button 
              className="btn-apply-update"
              onClick={handleApply}
              disabled={isCheckingOutput || hasOutput === null}
            > 
              Build QA System
            </button>
          )}
        </div>

        {/* <div className="apply-btn-row">
          <button 
            className="btn-apply-update"
            disabled={isAnyProcessing || isCheckingOutput || hasOutput === null}
          > 
            progress bar
          </button>
        </div> */}
        
        {/* <div className="result-table-section" id="info">
          <div className="header-bar">
            <div className="left-group">
              <h2 className="section-title">QA 시스템 정보 보기</h2>
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
            </div>
            <div className="search-bar">
              <div
                className={`search-wrapper ${isSearchHovered ? "expanded" : ""}`}
                onMouseEnter={() => setIsSearchHovered(true)}
                onMouseLeave={() => setIsSearchHovered(false)}
              >
                  <div className="search-icon">
                    🔍
                  </div>
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
                    className="search-input"
                  />
                </div>
              <div className="entity-count">
                {activeTab === "entity"
                  ? `총 엔티티 수: ${filteredEntities.length}`
                  : `총 엣지 수: ${filteredRelationships.length}`}
              </div>
            </div>
          </div>
          {activeTab === "entity" ? (
            <EntityTable entities={filteredEntities} />
          ) : (
            <RelationshipTable relationships={filteredRelationships} />
          )}
        </div> */}

        {/* 그래프 보기
        <div className="graph-section">
          <h2 className="section-title">QA 시스템 그래프 보기</h2>
          <button
            className="btn_primary"
            onClick={handleShowGraph}
            disabled={isAnyProcessing}
          >
            {showGraph ? "×" : "⏵"}
          </button>
        </div>

        {showGraph && graphData && (
          <div className="network-chart-wrapper">
            <NetworkChart data={graphData} />
          </div>
        )} */}
        
        {/* <div className="user-qa-analyze" id="user-questions">
          <h2 className="section-title">유저 질문 분석</h2>
          <div className="stat-cards">
            <div className="card card-total-category">
              <div className="card-text">
                많이 묻는 질문 카테고리<br /><strong>장학금</strong>
              </div>
            </div>
            <div className="card card-total-questions">
              <div className="card-text">
                사용자 질문 수<br /><strong>43231</strong>
              </div>
            </div>
            <div className="card card-avg-satisfaction">
              <div className="card-text">
                평균 만족도<br /><strong>4.7 / 5</strong>
              </div>
            </div>
          </div>
        </div> */}

        {/* <span className='user-table-info'>*정보 신뢰성: 제공한 정보의 정확성 평가</span> */}
        {/* <div className="upload-table-wrapper">
            <table className="user-table">
              <thead>
                <tr>
                  <th>질문</th>
                  <th>카테고리</th>
                  <th>만족도</th>
                  <th>정보 신뢰성</th>
                </tr>
              </thead>
              <tbody>
                {qaLoading ? (
                  <tr>
                    <td colSpan="4">QA 히스토리를 불러오는 중...</td>
                  </tr>
                ) : qaError ? (
                  <tr>
                    <td colSpan="4">QA 히스토리 로드 실패: {qaError}</td>
                  </tr>
                ) : qaHistory.length === 0 ? (
                  <tr>
                    <td colSpan="4">QA 히스토리가 없습니다.</td>
                  </tr>
                ) : (
                  qaHistory.map((item, index) => (
                    <tr key={item.id || index}>
                      <td>{item.question}</td>
                      <td>{item.category || "-"}</td>
                      <td>{item.satisfaction || "-"}</td>
                      <td>{item.trust || "-"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div> */}
        </div>
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

export default AdminPage;