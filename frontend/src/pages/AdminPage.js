import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import SidebarAdmin from "../components/navigation/SidebarAdmin";
import { usePageContext } from '../utils/PageContext';
import { useQAHistoryContext } from '../utils/QAHistoryContext'; // QA History Context 추가
import { FileDropHandler } from '../api/handleFileDrop';
import { fetchSavedUrls as fetchSavedUrlsApi, uploadUrl } from '../api/UrlApi';
import { checkOutputFolder as checkOutputFolderApi } from '../api/HasOutput';
import { processDocuments, loadUploadedDocs } from '../api/DocumentApi';
import { applyIndexing, updateIndexing } from '../api/IndexingButton';
import AdminHeader from '../services/AdminHeader';
import "../styles/AdminPage.css";
import ProgressingBar from '../services/ProgressingBar';
import { loadUploadedDocsFromFirestore } from '../api/UploadedDocsFromFirestore';
import LoadingSpinner from '../services/LoadingSpinner';
const BASE_URL = 'http://localhost:5000';

const AdminPage = () => {
    const navigate = useNavigate();
    const { pageId } = useParams();  // URL에서 페이지 ID 가져오기
    const [urlInput, setUrlInput] = useState("");
    const [uploadedUrls, setUploadedUrls] = useState([]);
    const [isNewPage, setIsNewPage] = useState(false);
    const [isLoadingPage, setIsLoadingPage] = useState(true);
    const [isUrlLoading, setIsUrlLoading] = useState(false);
    const [isFileLoading, setIsFileLoading] = useState(false);
    const [isProcessLoading, setIsProcessLoading] = useState(false);
    const [isApplyLoading, setIsApplyLoading] = useState(false);
    const [hasDocuments, setHasDocuments] = useState(false);
    const fileInputRef = useRef(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [duplicateFileName, setDuplicateFileName] = useState(null); //중복 파일 검사

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

    const [showProgressing, setShowProgressing] = useState(() => {
      const saved = localStorage.getItem(`showProgressing_${pageId}`);
      return saved === 'true';
    });
    const [docCount, setDocCount] = useState(0);  //문서 수
    const [urlCount, setUrlCount] = useState(0);
    const [conversionTime, setConversionTime] = useState(null); //문서 전처리 실행 시간
    const [applyExecutionTime, setApplyExecutionTime] = useState(null); //index 시간

    const { handleFileDrop } = useMemo(() => FileDropHandler({  //문서 수 firebase 실시간 연동
      uploadedDocs,
      setUploadedDocs,
      setDuplicateFileName,
      setIsFileLoading,
      setHasDocuments,
      isAnyProcessing,
      pageId,
      setDocCount
    }), [uploadedDocs, setUploadedDocs, setDuplicateFileName, setIsFileLoading, setHasDocuments, isAnyProcessing, pageId, setDocCount]);

    const handleCloseProgressing = async () => {
      setShowProgressing(false);
      localStorage.removeItem(`showProgressing_${pageId}`);

      if (!pageId) return;

      try {
        await checkOutputFolder(pageId);

        await Promise.all([
          fetchSavedUrls(pageId),
          loadDocumentsInfo(pageId)
        ]);
      } catch (error) {
        console.error('ProgressingBar 닫을 때 상태 갱신 오류:', error);
      }
    };

    // URL 목록 불러오기
    const fetchSavedUrls = useCallback(async (pageId) => {
      const urls = await fetchSavedUrlsApi(pageId);
      const urlArray = Array.isArray(urls) ? urls : [];
      setUploadedUrls(urlArray); // undefined 방지
      setUrlCount(urlArray.length);
    } , []);

    // 문서 정보 로드
    const loadDocumentsInfo = useCallback(async (pageId) => {
      if (!pageId) return;
      
      try {
        const res = await fetch(`${BASE_URL}/documents/${pageId}`);  // 문서 목록 api
        const data = await res.json();

        if (data.success) {
            const uploaded = data.uploaded_files;
            setUploadedDocs(data.uploaded_files);
            setHasDocuments(data.uploaded_files.length > 0);
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

    useEffect(() => {
      if (!pageId) {
        const savedPages = JSON.parse(localStorage.getItem("pages")) || [];
        if (savedPages.length > 0) {
          const fallbackPageId = savedPages[0].id;
          navigate(`/admin/${fallbackPageId}`);
        }
        return;
      }
      setIsLoadingPage(true);
      
      console.log("현재 admin pageId:", pageId);

      // 페이지가 변경될 때마다 상태 초기화
      // setEntities([]);
      // setRelationships([]);
      // setGraphData(null);
      // setUploadedUrls([]);
      // setUploadedDocs([]);
      // setHasDocuments(false);
      // setHasOutput(null);
      
      const savedShow = localStorage.getItem(`showProgressing_${pageId}`);
      if (savedShow === 'true') {
        setShowProgressing(true);
      } else {
        setShowProgressing(false);
      }
      
      if (pageId) {
        Promise.all([
          loadUploadedDocsFromFirestore(pageId)
            .then(({ docs, count }) => {
              const docsArray = Array.isArray(docs) ? docs : []; // 배열인지 확인
              setUploadedDocs(docsArray);
              setDocCount(count); // 문서 개수
            })
            .catch(error => {
              console.error("문서 목록 로드 중 오류:", error);
              setUploadedDocs([]);
              setDocCount(0);
            }),
          fetchSavedUrls(pageId),
          checkOutputFolder(pageId)
        ]).catch(error => console.error("데이터 로드 중 오류:", error))
          .finally(() => setIsLoadingPage(false)); // 로딩 종료
        
        const pages = JSON.parse(localStorage.getItem('pages')) || [];
        const currentPage = pages.find(page => page.id === pageId);
        if (currentPage) {
          setDomainName(currentPage.name || "");
          setSystemName(currentPage.sysname || "");
        }
      }
    }, [pageId, navigate]);

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
          setUrlCount(result.urls.length);
          setUrlInput('');
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
          setConversionTime(result.executionTime); 
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
      setShowProgressing(true);
      localStorage.setItem(`showProgressing_${pageId}`, 'true');
      setIsApplyLoading(true);

      try {
        const result = await applyIndexing(pageId);
        if (result.success) {
          setIsNewPage(false);
          setApplyExecutionTime(result.execution_time);

          // 인덱싱 완료 후 데이터 다시 로드
          await Promise.all([
            fetchSavedUrls(pageId).then(setUploadedUrls),
            loadDocumentsInfo(pageId),
            checkOutputFolder(pageId)
          ]);
        } else {
          alert(`문서 인덱싱 실패: ${result.error}`);
          setShowProgressing(false); // 실패 시에만 자동으로 닫기
        }
      } catch (error) {
        console.error("문서 인덱싱 중 오류:", error);
        alert("문서 인덱싱 중 오류가 발생했습니다.");
        setShowProgressing(false); // 에러 시에만 자동으로 닫기
      }finally {
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
            fetchSavedUrls(pageId).then(setUploadedUrls),
            loadDocumentsInfo(pageId),
            checkOutputFolder(pageId)
          ]);
        } else {
          alert(`업데이트 실패: ${result.error}`);
          setShowProgressing(false); 
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

    
    const handleAnalyzer = async () => {
      if (!pageId) {
        alert("먼저 페이지를 생성해주세요.");
        return;
      }

      if (isAnyProcessing) return;

      try {
        console.log("Analyzer 실행");

        navigate(`/dashboard/${pageId}`, { state: { conversionTime } });  //conversionTime : 문서 전처리 실행 시간
      } catch (error) {
        console.error("Analyzer 실행 중 오류:", error);
        alert("Analyzer 실행 중 오류가 발생했습니다.");
      }
    };

    return (
      <>
      {/* {isLoadingPage && <LoadingSpinner />} */}
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
                  onChange={(e) => setDomainName(e.target.value)} // 실시간 동기화 제거
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
                  
                  // localStorage도 함께 업데이트
                  const pages = JSON.parse(localStorage.getItem('pages')) || [];
                  const updatedPages = pages.map(page => {
                    if (page.id === pageId) {
                      return {
                        ...page,
                        name: domainName,
                        sysname: systemName
                      };
                    }
                    return page;
                  });
                  localStorage.setItem('pages', JSON.stringify(updatedPages));
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

              <div className="upload-table-wrapper">
                <table className="upload-table">
                  <thead>
                    <tr>
                      <th>URL</th>
                      <th>업로드 날짜</th>
                    </tr>
                  </thead>
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
                        <td colSpan={2} className="no-message">
                          업로드된 문서가 없습니다.<br />
                          url을 등록해주세요.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
             <div className='search-firebase-sum'>총 url 수: {urlCount}</div>
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

            <div className="document-table-scroll">
              <table className="document-table">
                <thead>
                  <tr>
                    <th>문서 이름</th>
                    <th>카테고리</th>
                    <th>업로드 날짜</th>
                  </tr>
                </thead>
                <tbody>
                  {Array.isArray(uploadedDocs) && uploadedDocs.length > 0 ? (
                    sortedDocs.map((doc, index) => (
                      <tr key={index}>
                        <td>{doc.original_filename}</td>
                        <td><span className="category-pill-admin">{doc.category}</span></td>
                        <td>{doc.date}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="no-message">
                        업로드된 문서가 없습니다.<br />
                        문서를 등록해주세요.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="search-firebase-sum">총 문서 수: {docCount}</div>
          </div>
        </div>

        {/* 적용 버튼 */}
        <div className="apply-btn-row">
          {showProgressing ? null : hasOutput ? (
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
                onClick={handleAnalyzer}
                disabled={isCheckingOutput}
              > 
                Go to Analyzer
              </button>
            </>
          ) : (
            <button 
              className="btn-apply-update"
              onClick={handleApply}
              disabled={isCheckingOutput || hasOutput === null}
            > 
              Build QA System
            </button>
          )}
        </div>

        {/* ProgressingBar는 중앙에 고정 */}
        {showProgressing && (
          <div className="progressing-overlay">
            <ProgressingBar 
              onClose={handleCloseProgressing}
              onAnalyzer={handleAnalyzer}   // 기존 버튼과 같은 함수
              isCompleted={hasOutput}       // output이 있을 때만 Analyzer 버튼 보여주기
              conversionTime={conversionTime} //문서 전처리 시간
              indexingTime={applyExecutionTime} //인덱싱 시간
            />
          </div>
        )}

        </div>
        <footer className="site-footer">
          <div className="footer-content">
            <p className="team-name">© 2025 황금토끼 팀</p>
            <p className="team-members">개발자: 옥지윤, 성주연, 김민서</p>
            <p className="footer-note">본 시스템은 한성대학교 QA 시스템 구축 프로젝트의 일환으로 제작되었습니다.</p>
          </div>
        </footer>
      </div>
      </>
    );
};

export default AdminPage;