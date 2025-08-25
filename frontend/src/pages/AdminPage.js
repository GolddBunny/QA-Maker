import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import SidebarAdmin from "../components/navigation/SidebarAdmin";
import { usePageContext } from '../utils/PageContext';
import { useQAHistoryContext } from '../utils/QAHistoryContext'; // QA History Context 추가
import { FileDropHandler } from '../api/handleFileDrop';
import { fetchSavedUrls as fetchSavedUrlsApi, uploadUrl } from '../api/UrlApi';
import { checkOutputFolder as checkOutputFolderApi } from '../api/HasOutput';
import { processDocuments, loadUploadedDocs } from '../api/DocumentApi';
import { applyIndexing, updateIndexing, executeFullPipeline } from '../api/IndexingButton';
import AdminHeader from '../services/AdminHeader';
import "../styles/AdminPage.css";
import ProgressingBar from '../services/ProgressingBar';
import { initDocUrl } from '../api/InitDocUrl';
import { loadUploadedDocsFromFirestore } from '../api/UploadedDocsFromFirestore';
import { doc, getDoc, setDoc, updateDoc } from "firebase/firestore";
import { db } from "../firebase/sdk";

const BASE_URL = 'http://localhost:5000/flask';

const calculateEstimatedTime = (urlCount, docCount, totalDocSizeMB = 0) => {
  // 기본 시간 (firebase에 저장하는 데 2분)
  const BASE_TIME = 2;
  
  // 각 항목별 평균 처리 시간 (초 단위)
  const DOC_STRUCTURING_TIME_PER_MB = 50; // 문서 1MB당 구조화 시간 (초)
  const DOC_INDEXING_TIME_PER_MB = 60;    // 문서 1MB당 인덱싱 시간 (초)
  const URL_STRUCTURING_TIME = 40;        // URL 1개당 구조화 시간 (초)
  const URL_INDEXING_TIME = 60;           // URL 1개당 인덱싱 시간 (초)
  
  // 총 처리 시간 계산 (초)
  const totalDocTime = totalDocSizeMB * (DOC_STRUCTURING_TIME_PER_MB + DOC_INDEXING_TIME_PER_MB);
  const totalUrlTime = urlCount * (URL_STRUCTURING_TIME + URL_INDEXING_TIME);
  const totalProcessingTime = totalDocTime + totalUrlTime;
  
  // 기본 시간 초로 변환 후 더하기
  const totalTimeInSeconds = totalProcessingTime + (BASE_TIME * 60);
  
  // 최종 분 단위로 변환
  const totalTimeInMinutes = Math.ceil(totalTimeInSeconds / 60);
  
  return {
    totalMinutes: totalTimeInMinutes,
    formattedTime: formatTime(totalTimeInMinutes),
    breakdown: {
      docStructuringTime: Math.ceil((totalDocSizeMB * DOC_STRUCTURING_TIME_PER_MB) / 60),
      docIndexingTime: Math.ceil((totalDocSizeMB * DOC_INDEXING_TIME_PER_MB) / 60),
      urlProcessingTime: Math.ceil(totalUrlTime / 60),
      baseTime: BASE_TIME
    }
  };
};

// 시간 "0시간 0분" 형식으로 변환
const formatTime = (minutes) => {
  if (minutes < 60) {
    return `${minutes}분`;
  } else {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    if (remainingMinutes === 0) {
      return `${hours}시간`;
    } else {
      return `${hours}시간 ${remainingMinutes}분`;
    }
  }
};

const AdminPage = () => {
    const navigate = useNavigate();
    const { pageId } = useParams();
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
    const [duplicateFileName, setDuplicateFileName] = useState(null);
    const [uploadedDocs, setUploadedDocs] = useState([]);

    const { currentPageId, updatePages, updatePageSysName, updatePageName,
      systemName, setSystemName, domainName, setDomainName
    } = usePageContext();

    // QA History 불러오기 (Firebase 기반)
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

    const [docCount, setDocCount] = useState(0); // 문서 수
    const [urlCount, setUrlCount] = useState(0); // URL 수
    const [conversionTime, setConversionTime] = useState(null); //문서 전처리 실행 시간
    const [applyExecutionTime, setApplyExecutionTime] = useState(null); //index 시간

    const [stepExecutionTimes, setStepExecutionTimes] = useState({
      crawling: null,
      structuring: null,
      document: null,
      indexing: null
    });
    
    const stepTimesRef = useRef(stepExecutionTimes);
    const [currentStep, setCurrentStep] = useState('crawling'); // 현재 진행 중인 단계

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

    // 전체 문서 용량 합계 (MB)
    const totalDocSizeMB = useMemo(() => {
      console.log('uploadedDocs:', uploadedDocs);
      const total = uploadedDocs.reduce((total, doc) => {
        console.log(`Document ${doc.original_filename}: size_mb = ${doc.size_mb}`);
        return total + (doc.size_mb || 0);
      }, 0);
      console.log('Total document size (MB):', total);
      return total;
    }, [uploadedDocs]);

    // 예상 처리 시간 계산
    const estimatedTime = useMemo(() => {
      return calculateEstimatedTime(urlCount, docCount, totalDocSizeMB);
    }, [urlCount, docCount, totalDocSizeMB]);

    const handleCloseProgressing = async () => {
      try {
        // 서버 작업 상태 확인
        const serverStatus = await checkServerProcessingStatus(pageId);
        
        if (serverStatus.isProcessing) {
          const confirmClose = window.confirm(
            "서버에서 작업이 진행 중입니다. 정말로 진행 창을 닫으시겠습니까?\n" +
            "창을 닫아도 서버 작업은 계속됩니다."
          );
          if (!confirmClose) return;
        }
        
        setShowProgressing(false);
        localStorage.removeItem(`showProgressing_${pageId}`);

        if (!pageId) return;

        await checkOutputFolder(pageId);
        await Promise.all([
          fetchSavedUrls(pageId),
          loadDocumentsInfo(pageId)
        ]);
      } catch (error) {
        console.error('ProgressingBar 닫을 때 상태 갱신 오류:', error);
      }
    };

    // 서버 작업 상태 확인
    const checkServerProcessingStatus = useCallback(async (pageId) => {
      if (!pageId) return { isProcessing: false };
      
      try {
        const response = await fetch(`${BASE_URL}/processing-status/${pageId}`);
        const data = await response.json();
        return data; // { isProcessing: true/false, currentStep: 'crawling'/'structuring'/etc, progress: 0.5 }
      } catch (error) {
        console.error("서버 작업 상태 확인 실패:", error);
        return { isProcessing: false };
      }
    }, []);

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
        const res = await fetch(`${BASE_URL}/documents/${pageId}`);
        const data = await res.json();
        console.log('API Response:', data); // 응답 구조 확인

        if (data.success) {
            const uploaded = data.uploaded_files;
            console.log('Uploaded files:', data.uploaded_files);
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
      stepTimesRef.current = stepExecutionTimes;

      const initializePage = async () => {
        try {
          // 1. 서버 작업 상태 먼저 확인
          const serverStatus = await checkServerProcessingStatus(pageId);
          
          // 2. localStorage 상태 확인
          const savedShow = localStorage.getItem(`showProgressing_${pageId}`);
          
          // 3. 서버에서 실제 작업 중이 아니면 localStorage 정리
          if (savedShow === 'true' && !serverStatus.isProcessing) {
            console.log("서버 작업이 중단됨. localStorage 정리");
            setShowProgressing(false);
            localStorage.removeItem(`showProgressing_${pageId}`);
          } else if (serverStatus.isProcessing) {
            // 4. 서버에서 작업 중이면 상태 복원
            console.log("서버 작업 진행 중. 상태 복원");
            setShowProgressing(true);
            setCurrentStep(serverStatus.currentStep || 'crawling');
            
            // 진행 상태에 따라 stepExecutionTimes 복원
            if (serverStatus.stepTimes) {
              setStepExecutionTimes(serverStatus.stepTimes);
            }
          } else {
            setShowProgressing(false);
          }

          // 5. 기존 데이터 로드
          await Promise.all([
            loadUploadedDocsFromFirestore(pageId)
              .then(({ docs, count }) => {
                const docsArray = Array.isArray(docs) ? docs : [];
                setUploadedDocs(docsArray);
                setDocCount(count);
              })
              .catch(error => {
                console.error("문서 목록 로드 중 오류:", error);
                setUploadedDocs([]);
                setDocCount(0);
              }),
            fetchSavedUrls(pageId),
            checkOutputFolder(pageId)
          ]);

          // 6. 페이지 정보 설정
          const pages = JSON.parse(localStorage.getItem('pages')) || [];
          const currentPage = pages.find(page => page.id === pageId);
          if (currentPage) {
            setDomainName(currentPage.name || "");
            setSystemName(currentPage.sysname || "");
          }
          
        } catch (error) {
          console.error("페이지 초기화 중 오류:", error);
        } finally {
          setIsLoadingPage(false);
        }
      };

      initializePage();
    }, [pageId, navigate, checkServerProcessingStatus, fetchSavedUrls, checkOutputFolder]);

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

    // 문서 구조화 함수
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

    // 각 단계 완료 시 호출되는 콜백 함수
    const handleStepComplete = async (stepName, durationInSeconds) => {
      setStepExecutionTimes(prev => {
        const updated = { ...prev, [stepName]: durationInSeconds };
        stepTimesRef.current = updated; 
        console.log("Updated stepExecutionTimes:", updated);
        return updated;
      });

      const stepOrder = ['crawling', 'structuring', 'document', 'indexing'];
      const nextIndex = stepOrder.indexOf(stepName) + 1;
      if (nextIndex < stepOrder.length) {
        setCurrentStep(stepOrder[nextIndex]);
      }

      if (!pageId) {
        console.warn("pageId가 없어 Firestore에 저장하지 못함");
        return;
      }

      try {
        const pageDocRef = doc(db, "dashboard", pageId);
        const docSnap = await getDoc(pageDocRef);

        if (docSnap.exists()) {
          await updateDoc(pageDocRef, {
            stepExecutionTimes: stepTimesRef.current,
          });
          console.log(`✅ Firestore에 stepExecutionTimes 업데이트 완료: ${stepName}`);
        } else {
          await setDoc(pageDocRef, {
            stepExecutionTimes: stepTimesRef.current,
          });
          console.log(`✅ Firestore에 stepExecutionTimes 새로 저장 완료: ${stepName}`);
        }
      } catch (error) {
        console.error("❌ Firestore 저장 실패:", error);
      }
    };

    // Q&A 시스템 생성 빌드 버튼 (크롤링 -> 구조화 -> 인덱싱)
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
         // 초기 상태 설정
        setCurrentStep('crawling');
        setStepExecutionTimes({
          crawling: null,
          structuring: null,
          document: null,
          indexing: null
        });

        const init_result = await initDocUrl(pageId);

        if (init_result.success) {
          console.log("초기화 성공:", init_result.message);
        } else {
          console.error("초기화 실패:", init_result.error);
        }

        // 크롤링 및 구조화
        const final_result = await executeFullPipeline(pageId, handleStepComplete);
        
        if (final_result.success) {
          setIsNewPage(false);

          console.log("=== 최종 실행시간 요약 ===");
          console.log("전체 실행시간:", final_result.execution_times.total, "초");

          // 인덱싱 완료 후 데이터 다시 로드
          await Promise.all([
            fetchSavedUrls(pageId).then(setUploadedUrls),
            loadDocumentsInfo(pageId),
            checkOutputFolder(pageId)
          ]);
        } else {
          alert(`QA 시스템 구축 실패: ${final_result.error}`);
          setShowProgressing(false); // 실패 시에만 자동으로 닫기
        }
      } catch (error) {
        console.error("QA 시스템 구축 중 오류:", error);
        alert("QA 시스템 구축 중 오류가 발생했습니다.");
        setShowProgressing(false); // 에러 시에만 자동으로 닫기
      }finally {
        setIsApplyLoading(false);
      }
    };

    // 업데이트 버튼 클릭 시
    const handleUpdate = async () => {
      if (uploadedDocs.length === 0 && uploadedUrls.length === 0) {
        alert("먼저 문서나 URL을 업로드해주세요.");
        return;
      }

      if (isAnyProcessing) return;
      setIsApplyLoading(true);
      const startTime = Date.now();

      try {
        const result = await updateIndexing(pageId);
        const endTime = Date.now();

        if (result.success) {
          const durationInSeconds = Math.round((endTime - startTime) / 1000);
          setStepExecutionTimes(prev => ({
            ...prev,
            update: durationInSeconds
          }));

          alert("업데이트 완료");

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

    // Log Analyzer로 이동 버튼 클릭 시
    const handleAnalyzer = () => {
      const allDone = Object.values(stepExecutionTimes).every(v => v !== null);

      console.log("최종 stepExecutionTimes로 navigate:", stepExecutionTimes);
      navigate(`/dashboard/${pageId}`, {
        state: { stepExecutionTimes: stepExecutionTimes } // state 직접 사용
      });
    };

    // 사용자 만족도 페이지로 이동 버튼 클릭 시
    const handleUserDashboard = () => {
      console.log("UserDashboard로 navigate:", pageId);
      navigate(`/userDashBoard/${pageId}`);
    };

    return (
      <>
      <div className={`admin-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
        {/* 헤더 */}
        <AdminHeader isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />

        {/* 사이드바는 AdminPage 안에서만 조건부 렌더링 */}
        {isSidebarOpen && (
          <SidebarAdmin
            isSidebarOpen={isSidebarOpen}
            toggleSidebar={toggleSidebar}
          />
        )}
        
        {/* 본문 */}
        <div className={`admin-content ${isSidebarOpen ? 'sidebar-open' : ''}`}>
          {/* 상단 입력부 */}
          <div className="input-container" id="name">
            <div className="input-row-horizontal">
              {/* 시스템 이름/도메인 이름 입력부 */}
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
                placeholder={isAnyProcessing ? '처리 중 ...' : 'https://example.com'}
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
                  {Array.isArray(uploadedUrls) && uploadedUrls.length > 0 ?  (
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
                
                {/* 처리 중이면 전용 메시지 보여주기 */}
                {isAnyProcessing ? (
                  <p>처리 중...</p>
                ) : (
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
              <button 
                className="btn-apply-update"
                onClick={handleUserDashboard}
                disabled={isCheckingOutput}
              > 
                Go to UserDashboard
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
          <ProgressingBar
            onClose={() => {
              setShowProgressing(false);
              localStorage.removeItem(`showProgressing_${pageId}`);
            }}
            onAnalyzer={() => navigate(`/dashboard/${pageId}`, {
              state: { stepExecutionTimes: stepTimesRef.current }
            })}
            isCompleted={!isApplyLoading} // 로딩이 끝나면 완료
            stepExecutionTimes={stepExecutionTimes} // 각 단계별 실행시간
            currentStep={currentStep} // 현재 진행 중인 단계
            estimatedTime={estimatedTime} // 새로 추가된 prop
          />
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