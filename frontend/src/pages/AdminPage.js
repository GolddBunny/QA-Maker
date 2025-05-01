import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import "../styles/AdminPage.css";
import SidebarAdmin from "../components/navigation/SidebarAdmin";

const BASE_URL = 'http://localhost:5000';
const UPLOAD_URL = `${BASE_URL}/upload-documents`;
const PROCESS_URL = `${BASE_URL}/process-documents`;
const UPDATE_URL = `${BASE_URL}/update`;
const APPLY_URL = `${BASE_URL}/apply`;
const URL_URL = `${BASE_URL}`;

const allowedFileTypes = ['application/pdf', 'text/plain', 'text/csv', 'application/json', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];

const AdminPage = () => {
    const navigate = useNavigate();
    const { pageId } = useParams();  // URL에서 페이지 ID 가져오기
    const [urlInput, setUrlInput] = useState("");
    const [uploadedUrls, setUploadedUrls] = useState([]);
    const [uploadedDocs, setUploadedDocs] = useState([]);
    const [currentPageId, setCurrentPageId] = useState(null);
    const [isNewPage, setIsNewPage] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [hasDocuments, setHasDocuments] = useState(false);
    const fileInputRef = useRef(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    useEffect(() => {
      let savedPageId = pageId;  // URL에서 페이지 ID 가져오기
      if (!savedPageId) {
          savedPageId = localStorage.getItem('currentPageId');
      }

      if (!savedPageId) {
          // 기본 페이지 ID로 이동
          const savedPages = JSON.parse(localStorage.getItem('pages')) || [];
          savedPageId = savedPages[0]?.id || null;
      }

      setCurrentPageId(savedPageId);
      localStorage.setItem('currentPageId', savedPageId);  // 현재 페이지 ID 저장

      // 해당 페이지의 문서 목록 로드
      if (savedPageId) {
        const savedDocs = JSON.parse(localStorage.getItem(`uploadedDocs_${savedPageId}`)) || [];
        setUploadedDocs(savedDocs);
        setHasDocuments(savedDocs.length > 0);
        
        setIsNewPage(savedDocs.length === 0);
      
        fetchSavedUrls(savedPageId); // URL 목록 불러오기
      }
    }, [pageId]);

    const toggleSidebar = () => {
      setIsSidebarOpen(!isSidebarOpen);
    };
    
    const handleDragOver = (e) => {
      if (isLoading) return;

      e.preventDefault();
      setIsDragOver(true);
    };

    const handleDragLeave = () => {
      if (isLoading) return;

      setIsDragOver(false);
    };

    const handleFileDrop =async(e) => {
        e.preventDefault();
        setIsDragOver(false);

        if (isLoading) return;
        setIsLoading(true);

        try {
          const files = Array.from(e.dataTransfer ? e.dataTransfer.files : e.target.files);
          
          // 파일 확장자 필터링
          const filteredFiles = files.filter(file => allowedFileTypes.includes(file.type));

          if (filteredFiles.length === 0) {
              alert(".pdf, .txt, .csv, .json, .xlsx 파일만 업로드할 수 있습니다.");
              return;
          }

          // 이미 업로드한 문서가 있는지 확인
          const existingDocs = uploadedDocs.map(doc => doc.toLowerCase());
          const newFiles = filteredFiles.filter(file => !existingDocs.includes(file.name.toLowerCase()));

          if (newFiles.length === 0) {
              alert("이미 업로드된 문서입니다.");
              return;
          }

          const formData = new FormData();
          files.forEach(file => {
              formData.append('files', file);
          });

          const response = await fetch(`${UPLOAD_URL}/${currentPageId}`, {
            method: 'POST',
            body: formData
          });

          const data = await response.json();
          if (data.success) {
            // 업로드된 파일명 추가
            const newDocs = [...uploadedDocs, ...newFiles.map(file => file.name)];
            setUploadedDocs(newDocs);
            setHasDocuments(true);
            
            // 로컬 스토리지에 업로드된 문서 목록 저장
            localStorage.setItem(`uploadedDocs_${currentPageId}`, JSON.stringify(newDocs));
          } else {
              console.error('파일 업로드 실패:', data.error);
              alert('파일 업로드에 실패했습니다.');
          }
        } catch (error) {
            console.error('파일 업로드 오류:', error);
            alert('파일 업로드 중 오류가 발생했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    // URL 목록 불러오기
    const fetchSavedUrls = async (pageId) => {
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
      
      // URL 유효성 검사
      if (!isValidUrl(urlInput)) {
        alert('유효한 URL을 입력해주세요');
        return;
      }
      setIsLoading(true);
      
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
          setUploadedUrls([...uploadedUrls, urlInput]);
          setUrlInput('');
          alert("URL이 등록되었습니다.");
        } else {
          throw new Error('URL 저장 실패: ' + data.error);
        }
      } catch (error) {
        console.error('URL 추가 오류:', error);
        alert('오류 발생: ' + error.message);
      } finally {
        setIsLoading(false);
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
      setIsLoading(true);

      try {
        // 문서 처리 요청
        const response = await fetch(`${PROCESS_URL}/${currentPageId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('문서 처리 완료');
            setIsNewPage(false);
        } else {
            console.error('문서 처리 실패:', data.error);
            alert('문서 처리에 실패했습니다.');
        }
      } catch (error) {
          console.error('문서 처리 중 오류:', error);
          alert('문서 처리 중 오류가 발생했습니다.');
      } finally {
          setIsLoading(false);
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
      setIsLoading(true);
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
        setIsLoading(false);
      }
    };

    const handleUpdate = async() => {
      if (uploadedDocs.length === 0 && uploadedUrls.length === 0) {
        alert("먼저 문서나 URL을 업로드해주세요.");
        return;
      }

      setIsLoading(true);

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
        setIsLoading(false);
      }
    }

    return (
      <div className={`admin-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
        <h1>{currentPageId ? `페이지 ID: ${currentPageId}` : '페이지를 선택하세요.'}</h1>
        <SidebarAdmin isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
        <h3>업로드된 URL</h3>
        <div className="list-container">
        {uploadedUrls.length > 0 ? (
          uploadedUrls.map((url, index) => (
            <div key={index}>{url}</div>
          ))
        ) : (
          <div>업로드된 URL이 없습니다.</div>
        )}
        </div>
        
        <h3>업로드된 문서</h3>
        <div className="list-container">
        {uploadedDocs.map((doc, index) => (
            <div key={index}>{doc}</div>
        ))}
        </div>
        
        <h3>URL 업로드</h3>
        <div className="input-container">
          <input
            type="text"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://example.com"
            className="input-field"
            disabled={isLoading}
          />
          <button 
            className="url-check-btn" 
            onClick={handleUrlUpload}
            disabled={isLoading}
          >
            {isLoading ? '처리 중' : 'URL 등록'}
        </button>
        </div>
        
        <h3>문서 업로드</h3>
        <div className="upload-container">
          <div
            className={`upload-section ${isDragOver ? 'drag-over' : ''} ${isLoading ? 'disabled' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleFileDrop}
            onClick={() => !isLoading && fileInputRef.current.click()}
            >
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              multiple
              accept=".pdf, .txt, .csv, .json, .xlsx"
              onChange={handleFileDrop}
              disabled={isLoading}
            />
            <p>{isLoading ? '처리 중...' : (isDragOver ? '여기에 파일을 놓으세요' : '파일을 여기로 드래그하거나 클릭하세요')}</p>
          </div>
          <button
            className="process-btn"
            onClick={handleProcessDocuments}
            disabled={isLoading}
          >
            {isLoading ? '처리 중' : '문서 등록'}
          </button>
        </div>
        
        <div className="button-group">
          <button 
            className="apply-btn"
            onClick={isNewPage ? handleApply : handleUpdate}
            disabled={isLoading}
          > 
            {isLoading ? '처리 중' : (isNewPage ? 'Apply' : 'Update')}
          </button>
        </div>
      </div>
    );
};

export default AdminPage;