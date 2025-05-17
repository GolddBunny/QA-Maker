import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import "../styles/AdminPage.css";
import SidebarAdmin from "../components/navigation/SidebarAdmin";
import NetworkChart from "../components/charts/NetworkChart";
import { getCurrentPageId, getPages, savePages } from '../utils/storage'; // 유틸리티 함수 임포트
import { usePageContext } from '../utils/PageContext';


const BASE_URL = 'http://localhost:5000';
const UPLOAD_URL = `${BASE_URL}/upload-documents`;
const PROCESS_URL = `${BASE_URL}/process-documents`;
const UPDATE_URL = `${BASE_URL}/update`;
const APPLY_URL = `${BASE_URL}/apply`;
const URL_URL = `${BASE_URL}`;

const allowedFileTypes = [
  'application/pdf',
  'text/plain',
  'application/octet-stream', //hwp
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
  'application/msword' // .doc
];

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

    // 작업 처리 중인지 확인 상태
    const isAnyProcessing = isUrlLoading || isFileLoading || isProcessLoading || isApplyLoading;

    
    const fetchGraphData = useCallback(async (pageId) => {
      if (!pageId) return;
      const cacheKey = `graphData-${pageId}`;

      if (graphDataCacheRef.current[cacheKey]) {
        console.log("그래프 데이터 캐시에서 로드됨");
        setGraphData(graphDataCacheRef.current[cacheKey]);
        return;
      }

      // 2. 로컬 JSON 파일에서 로딩 시도
      const loadGraphFromLocalJson = async () => {
        const filePath = `/json/${pageId}/admin_graphml_data.json`;
        try {
          const res = await fetch(filePath, { cache: 'no-store' });
          if (res.ok) {
            const data = await res.json();
            console.log("로컬 JSON 파일에서 그래프 데이터 로드됨");
            return data;
          } else {
            console.log("로컬 JSON 파일 없음 또는 로딩 실패");
            return null;
          }
        } catch (err) {
          console.error("로컬 JSON 로딩 중 오류:", err);
          return null;
        }
      };

      const generateGraphViaServer = async () => {
        console.log("서버로 그래프 생성 요청 전송 중...");
        const res = await fetch(`${BASE_URL}/admin/all-graph`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
          },
          body: JSON.stringify({ page_id: pageId }),
        });
        console.log("서버 응답 상태:", res.status);
        if (!res.ok) throw new Error(`서버 그래프 생성 실패: ${res.status}`);

        // 응답 결과가 JSON 직접 포함되어 있다고 가정
        return await res.json();
      };

      try {
        let data = await loadGraphFromLocalJson();
        if (!data) {
          data = await generateGraphViaServer();
        }

        if (data) {
          graphDataCacheRef.current[cacheKey] = data;
          setGraphData(data);
        }
      } catch (err) {
        console.error("그래프 데이터 로드 중 오류:", err);
      }
    }, []);

    const fetchEntities = useCallback(async (id) => {
      if (!id) return null;
      
      try {
        const res = await fetch(`${BASE_URL}/api/entity/${id}`);
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(`Entity fetch error: ${res.statusText}, Details: ${JSON.stringify(errorData)}`);
        }
        const data = await res.json();
        return data;
      } catch (err) {
        console.error("entity fetch error:", err);
        setDataFetchError("엔티티 데이터 로드 실패");
        return [];
      }
    }, []);

    // 관계 데이터 로드
    const fetchRelationships = useCallback(async (id) => {
      if (!id) return null;
      
      try {
        const res = await fetch(`${BASE_URL}/api/relationship/${id}`);
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(`Relationship fetch error: ${res.statusText}, Details: ${JSON.stringify(errorData)}`);
        }
        const data = await res.json();
        return data;
      } catch (err) {
        console.error("relationship fetch error:", err);
        setDataFetchError("관계 데이터 로드 실패");
        return [];
      }
    }, []);

    // URL 목록 불러오기
    const fetchSavedUrls = useCallback(async (pageId) => {
      try {
        const response = await fetch(`${URL_URL}/get-urls/${pageId}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        const data = await response.json();
        
        if (data.success) {
          setUploadedUrls(data.urls || []);
        } else {
          console.error('URL 목록 불러오기 실패:', data.error);
        }
      } catch (error) {
        console.error('URL 목록 불러오기 오류:', error);
      }
    }, []);

    // 문서 정보 로드
    const loadDocumentsInfo = useCallback(async (id) => {
      if (!id) return;
      
      try {
        const savedDocs = JSON.parse(localStorage.getItem(`uploadedDocs_${id}`)) || [];
        setUploadedDocs(savedDocs);
        setHasDocuments(savedDocs.length > 0);
        setIsNewPage(savedDocs.length === 0);
      } catch (error) {
        console.error("문서 정보 로드 실패:", error);
      }
    }, []);

    // Output 폴더 확인
    const checkOutputFolder = useCallback(async (pageId) => {
      try {
        const response = await fetch(`${BASE_URL}/has-output/${pageId}`);
        const data = await response.json();

        if (data.success) {
          setIsNewPage(!data.has_output);  // 있으면 Update, 없으면 Apply
        } else {
          console.warn("서버가 output 폴더 상태를 반환하지 않음.");
        }
      } catch (err) {
        console.error("Output 폴더 확인 실패:", err);
      }
    }, []);

    const loadAllData = useCallback(async (id) => {
      if (!id) return;
      
      setLoading(true);
      setDataFetchError(null);
      
      try {
        // 병렬로 데이터 로드
        const [entitiesData, relationshipsData] = await Promise.all([
          fetchEntities(id),
          fetchRelationships(id)
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
    }, [fetchEntities, fetchRelationships]);

    useEffect(() => {
      if (currentPageId) {
        const saved = localStorage.getItem(`uploadedDocs_${currentPageId}`);
        setUploadedDocs(saved ? JSON.parse(saved) : []);
      }
      let savedPageId = pageId;  // URL에서 페이지 ID 가져오기
      
      // 페이지 ID가 유효한 경우에만 데이터 로드
      if (savedPageId) {
        // 병렬로 데이터 로드 작업 실행
        Promise.all([
          loadDocumentsInfo(savedPageId),
          fetchSavedUrls(savedPageId),
          checkOutputFolder(savedPageId),
          loadAllData(savedPageId),
          //fetchGraphData(savedPageId) 
        ]).catch(error => {
          console.error("데이터 로드 중 오류:", error);
        });
        const pages = JSON.parse(localStorage.getItem('pages')) || [];
        const currentPage = pages.find(page => page.id === savedPageId);
        if (currentPage) {
          setDomainName(currentPage.name || "");
          setSystemName(currentPage.sysname || "");
        }
      }
    }, [pageId, loadDocumentsInfo, fetchSavedUrls, checkOutputFolder, loadAllData, fetchGraphData]);


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

    const handleFileDrop = async(e) => {
        e.preventDefault();
        setIsDragOver(false);

        if (isAnyProcessing) return;
        setIsFileLoading(true);

        try {
          const files = Array.from(e.dataTransfer ? e.dataTransfer.files : e.target.files);
          
          // 파일 확장자 필터링
          const filteredFiles = files.filter(file => {
            const isAllowedType = allowedFileTypes.includes(file.type);
            const isHwpFile = file.name.toLowerCase().endsWith('.hwp');
            return isAllowedType || isHwpFile;
          });

          if (filteredFiles.length === 0) {
              alert(".pdf, .hwp, .docx, .txt 파일만 업로드할 수 있습니다.");
              return;
          }

          // 이미 업로드한 문서가 있는지 확인
          const existingDocs = uploadedDocs.map(doc => doc.name.toLowerCase());
          const newFiles = filteredFiles.filter(file => !existingDocs.includes(file.name.toLowerCase()));

          if (newFiles.length === 0) {
            setDuplicateFileName(filteredFiles[0].name); // 첫 번째 중복 파일 이름만 표시
            return;
          }

          const formData = new FormData();
          newFiles.forEach(file => {
              formData.append('files', file);
          });

          const response = await fetch(`${UPLOAD_URL}/${currentPageId}`, {
            method: 'POST',
            body: formData
          });

          const data = await response.json();
          if (!data.success) {
            alert('파일 업로드에 실패했습니다.');
            return;
          }

          // 오늘 날짜 (YYYY-MM-DD)
          const today = new Date().toISOString().split('T')[0];
          // 새로 추가할 문서 객체 리스트
          const newDocObjs = newFiles.map(file => ({
            name: file.name,
            category: '학교',   // 임시로 고정
            date: today
          }));

          // 상태 및 로컬스토리지 업데이트
          const updated = [...uploadedDocs, ...newDocObjs];
          setUploadedDocs(updated);
          localStorage.setItem(`uploadedDocs_${currentPageId}`, JSON.stringify(updated));
          setHasDocuments(true);

        } catch (error) {
            console.error('파일 업로드 오류:', error);
            alert('파일 업로드 중 오류가 발생했습니다.');
        } finally {
            setIsFileLoading(false);
        }
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
      if (urlInput.trim() === '') {
        return;
      }
      
      if (isAnyProcessing) return;
      
      // URL 유효성 검사
      if (!isValidUrl(urlInput)) {
        alert('유효한 URL을 입력해주세요');
        return;
      }
      setIsUrlLoading(true);
      
      try {
        // URL 저장 및 크롤링 즉시 실행
        const response = await fetch(`${URL_URL}/add-url/${currentPageId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            url: urlInput
          }),
        });
        
        const data = await response.json();
        
        if (data.success) {
          console.log('URL 저장 완료:', data);
          
          // 처리 완료된 URL을 업로드된 목록에 추가
          setUploadedUrls(data.urls || []);
          setUrlInput('');
          alert("URL이 등록되었습니다.");
        } else {
          throw new Error('URL 저장 실패: ' + data.error);
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
      if (!currentPageId) {
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
        // 문서 처리 요청
        const response = await fetch(`${PROCESS_URL}/${currentPageId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('문서 처리 완료');
        } else {
            console.error('문서 처리 실패:', data.error);
            alert('문서 처리에 실패했습니다.');
        }
      } catch (error) {
          console.error('문서 처리 중 오류:', error);
          alert('문서 처리 중 오류가 발생했습니다.');
      } finally {
          setIsProcessLoading(false);
      }
    };

    const handleApply = async () => {
      if (!currentPageId) {
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
        const response = await fetch(`${APPLY_URL}/${currentPageId}`, {
          method: 'POST'
        });
    
        const data = await response.json();

        if (data.success) {
          alert("문서 인덱싱 완료");
          setIsNewPage(false);
        } else {
          alert(`문서 인덱싱 실패: ${data.error}`);
        }
      } catch (err) {
        console.error('인덱싱 요청 중 오류:', err);
        alert("문서 인덱싱 중 오류가 발생했습니다.");
      } finally {
        setIsApplyLoading(false);
      }
    };

    const handleUpdate = async() => {
      if (uploadedDocs.length === 0 && uploadedUrls.length === 0) {
        alert("먼저 문서나 URL을 업로드해주세요.");
        return;
      }

      if (isAnyProcessing) return;
      
      setIsApplyLoading(true);

      try {
        const response = await fetch(`${UPDATE_URL}/${currentPageId}`, {
          method: 'POST'
        });

        const data = await response.json();

        if(data.success) {
          alert('업데이트 완료');
        } else {
          console.error('update failed');
          alert('업데이트에 실패했습니다.');
        } 
      } catch(error) {
        console.error('error in try-catch for updating:', error);
        alert('업데이트 중 오류 발생');
      } finally {
        setIsApplyLoading(false);
      }
    };

    const renderEntityTable = () => (
      <>
        <div className="result-table-wrapper">
          <table className="result-table">
            <thead>
              <tr>
                <th>id</th>
                <th>title</th>
                <th>description</th>
              </tr>
            </thead>
            <tbody>
              {filteredEntities.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.id}</td>
                  <td>{item.title}</td>
                  <td>{item.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    );

    const renderRelationshipTable = () => (
      <>
        <div className="result-table-wrapper">
          <table className="result-table">
            <thead>
              <tr>
                <th>id</th>
                <th>source</th>
                <th>target</th>
                <th>description</th>
              </tr>
            </thead>
            <tbody>
              {filteredRelationships.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.id}</td>
                  <td>{item.source}</td>
                  <td>{item.target}</td>
                  <td>{item.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    );
    
    const filteredEntities = entities
      .filter((item) =>
        item.title && item.title.toLowerCase().includes(entitySearchTerm.toLowerCase())
      )
      .sort((a, b) => a.id - b.id);

    const filteredRelationships = relationships
      .filter(
        (item) =>
          item.description &&
          item.description.toLowerCase().includes(relationshipSearchTerm.toLowerCase())
      )
      .sort((a, b) => a.id - b.id);

    const handleShowGraph = () => {
      if (!graphData && currentPageId) {
        fetchGraphData(currentPageId);
      }
      setShowGraph(true);
    };
    

    

    return (
      <div className={`admin-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
        <SidebarAdmin isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />

        {/* 상단 입력부 */}
        <div className="input-container">
          <div className="input-group">
            <div className="input-field">
              <label>도메인 이름</label>
              <input
                type="text"
                placeholder="도메인 이름을 정해주세요"
                value={domainName}  // 상태로 관리되는 도메인 이름
                onChange={(e) => setDomainName(e.target.value)} // input 변화에 따른 상태 업데이트
              />
            </div>
            <div className="divider"></div>
            <div className="input-field">
              <label>검색 시스템 이름</label>
              <input
                type="text"
                placeholder="검색 시스템 이름을 정해주세요"
                value={systemName}
                onChange={(e) => setSystemName(e.target.value)}
              />
            </div>
            <button className="apply-button-admin" onClick={() => {
              // 도메인 이름 업데이트
              const nameResult = updatePageName(currentPageId, domainName);
              // 시스템 이름 업데이트
              const sysNameResult = updatePageSysName(currentPageId, systemName);
              // 각 업데이트 결과에 따라 개별적으로 상태 업데이트
                if (nameResult.success) {
                  console.log("[적용 버튼] 도메인 이름 업데이트 성공:", domainName);
                } else {
                  console.error("[적용 버튼] 도메인 이름 업데이트 실패:", nameResult.error);
                }
                
                if (sysNameResult.success) {
                  console.log("[적용 버튼] 시스템 이름 업데이트 성공:", systemName);
                } else {
                  console.error("[적용 버튼] 시스템 이름 업데이트 실패:", sysNameResult.error);
                }
              }}>적용하기
            </button>
          </div>
          
        </div>

        {/* 상단 통계 카드
        <div className="stat-cards">
        <div className="card card-total-url">
          <div className="card-text">
            총 URL 수<br /><strong>43231</strong>
          </div>
        </div>
        <div className="card card-total-docs">
          <div className="card-text">
            총 문서 수<br /><strong>43231</strong>
          </div>
        </div>
        <div className="card card-total-entities">
          <div className="card-text">
            총 엔티티 수<br /><strong>43231</strong>
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
      </div> */}
        
        {/* <h1>{currentPageId ? `페이지 ID: ${currentPageId}` : '페이지를 선택하세요.'}</h1> */}

        <div className="upload-section-wrapper">
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
                placeholder={"https://example.com"}
                className="url-input-field"
                disabled={isAnyProcessing}
                style={{ color: isAnyProcessing ? 'transparent' : 'inherit' }}
              />
              {isAnyProcessing && (
                  <div className="loader processing-message">
                    {"Loading".split("").map((char, i) => (
                      <span key={i} className={`letter ${char === " " ? "i" : char}`}>
                        {char}
                      </span>
                    ))}
                  </div>
                )}

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
                    <tr>
                      <td colSpan="2" className="empty-message">업로드된 URL이 없습니다.</td>
                    </tr>
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
                
                {/* 처리 중 메시지 */}
                {isAnyProcessing && (
                  <div className="loader processing-message">
                    {"Loading".split("").map((char, i) => (
                      <span key={i} className={`letter ${char === " " ? "i" : char}`}>
                        {char}
                      </span>
                    ))}
                  </div>
                )}

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
                        uploadedDocs.map((doc, index) => (
                          <tr key={index}>
                            <td>{doc.name}</td>
                            <td><span className="category-pill">{doc.category}</span></td>
                            <td>{doc.date}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="3" className="empty-message">업로드된 문서가 없습니다.</td>
                        </tr>
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
          <button 
            className="btn-apply-update"
            onClick={isNewPage ? handleApply : handleUpdate}
            disabled={isAnyProcessing}
          > 
            {isAnyProcessing ? 'QA 생성 중' : 'QA 생성 시작'}
          </button>
        </div>
        
        <div className="result-table-section">
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
          {activeTab === "entity" ? renderEntityTable() : renderRelationshipTable()}
        </div>

        {/* 그래프 보기 */}
        <h2 className="section-title">그래프 보기</h2>
        <button
          className="btn_primary"
          onClick={handleShowGraph}
          disabled={isAnyProcessing}
        >
          그래프 보기
        </button>

        {showGraph && graphData && (
          <div className="network-chart-wrapper">
            <NetworkChart data={graphData} />
          </div>
        )}
        <h2 className="section-title">유저 질문 및 만족도 분석</h2>
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

        <div className="upload-table-wrapper">
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
                
              </tbody>
            </table>
          </div>

      </div>
    );
};

export default AdminPage;