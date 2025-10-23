import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/MainPage.css";
import Sidebar from "../components/navigation/Sidebar";
import { usePageContext } from '../utils/PageContext';
import { findMainPage } from '../utils/storage';
import { loadUploadedDocsFromFirestore } from '../api/UploadedDocsFromFirestore';
import { fetchSavedUrls as fetchSavedUrlsApi, uploadUrl } from '../api/UrlApi';
import { GetEntitiesCount } from '../api/GetEntitiesCount';

function MainPage() {
  const { currentPageId, setCurrentPageId } = usePageContext(); 
  const [message, setMessage] = useState('');
  const [isDropdownVisible, setIsDropdownVisible] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [searchType, setSearchType] = useState('url');
  const [selectedFile, setSelectedFile] = useState(null);
  const { systemName } = usePageContext();
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);

  const [urlInput, setUrlInput] = useState('');
  const [addedUrls, setAddedUrls] = useState([]);
  const [showUrlInput, setShowUrlInput] = useState(false);

  // 문서, URL, 엔티티 개수 상태 추가
  const [docCount, setDocCount] = useState(0);
  const [urlCount, setUrlCount] = useState(0);
  const [entityCount, setEntityCount] = useState(0);

  useEffect(() => {
    const fetchMainPage = async () => {
      try {
        const mainPage = await findMainPage();
        if (mainPage) {
          setCurrentPageId(mainPage.id);
          localStorage.setItem('currentPageId', mainPage.id);
          console.log("기본 페이지 ID 설정:", mainPage.id);
        } else {
          console.log("기본 페이지를 Firebase에서 찾을 수 없습니다.");
        }
      } catch (error) {
        console.error("메인 페이지 가져오기 중 오류:", error);
      }
    };

    fetchMainPage();
  }, [setCurrentPageId]);

  // 문서, URL, 엔티티 개수 가져오기
  useEffect(() => {
    const fetchCounts = async () => {
      if (!currentPageId) return;

      try {
        // 문서 개수
        const { count: documentCount } = await loadUploadedDocsFromFirestore(currentPageId);
        setDocCount(documentCount.toLocaleString() || 0);

        // URL 개수
        const urls = await fetchSavedUrlsApi(currentPageId);
        const urlArray = Array.isArray(urls) ? urls : [];
        setUrlCount(urlArray.length.toLocaleString() || 0);

        // 엔티티 개수
        const entitiesResult = await GetEntitiesCount(currentPageId);
        if (entitiesResult.success) {
          setEntityCount(entitiesResult.totalCount.toLocaleString());
          console.log('엔티티 개수 업데이트:', entitiesResult);
        } else {
          console.error('엔티티 개수 가져오기 실패:', entitiesResult.error);
          setEntityCount(0);
        }

      } catch (error) {
        console.error("개수 가져오기 중 오류:", error);
        setDocCount(0);
        setUrlCount(0);
        setEntityCount(0);
      }
    };

    if (currentPageId) {
      fetchCounts();
    }
  }, [currentPageId]);

  // 사이드바
  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // 검색
  const handleSearch = (e) => {
    e?.preventDefault();
    if (!message.trim() && !selectedFile) return;
    
    e?.preventDefault();
     if (!message.trim()) return;
     navigate(`/chat?question=${encodeURIComponent(message.trim())}`);
   };
  
  // Enter 키 처리 함수
  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch();
    }
  };

  // 파일 선택 처리 함수
  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      console.log('선택된 파일:', file.name);
    }
  };

  // 문서 버튼 클릭 시 파일 선택창 열기
  const handleDocumentOptionClick = () => {
    setSearchType('document');
    fileInputRef.current.click();
    setIsDropdownVisible(false);
  };

  // URL 선택 시 처리
  const handleUrlOptionClick = () => {
    setSearchType('url');
    setShowUrlInput(true); // 입력창 보이게
  };

  // URL 추가
  const handleAddUrl = () => {
    const urlPattern = /^(https?:\/\/)?([\w-]+\.)+[\w-]{2,}(\/\S*)?$/;
    if (!urlPattern.test(urlInput.trim())) {
      alert('유효한 URL을 입력해주세요.');
      return;
    }

    setAddedUrls([...addedUrls, urlInput.trim()]);
    setUrlInput('');
    setShowUrlInput(false); // 입력창 닫기
  };

  const headerText = "무엇이든 물어보세요 ";
  const headerLetters = headerText.split('');
  
  return (
    <div className={`container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      <Sidebar isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />

      {/* 상단 버튼 */}
      <div className="top-buttons">
        <div>
          <div className="stats">URL 수 {urlCount}</div>
          {/* <div className="stats">URL 수 802</div> */}

        </div>
        <span className="stats-divider">|</span>
        <div>
          <div className="stats">문서 수 {docCount}</div>
        </div>
        <span className="stats-divider">|</span>
        <div>
          <div className="stats">엔티티 수 {entityCount}</div>
        </div>
      </div>

      {/* 제목 애니메이션 */}
      <h1> 💡 
        {headerLetters.map((letter, index) => (
          <span key={index}>
            {letter === ' ' ? '\u00A0' : letter}
          </span>
        ))}
      </h1>

      <div className="typing-text">
        {systemName}에서 찾아볼게요!
      </div>

      <div className="search-container">
        <textarea
          type="text"
          id="search-input"
          placeholder="질문을 입력하세요"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyPress}
        />

        <button className="icon-btn" onClick={handleSearch}>
          <svg className="icon" viewBox="0 0 24 24">
            <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="2" fill="none" />
            <line x1="14.5" y1="14.5" x2="20" y2="20" stroke="currentColor" strokeWidth="2" />
          </svg>
        </button>

        {/* <div className="bottom-left-buttons">
          <button className="url-btn" onClick={handleUrlOptionClick}>URL 추가하기</button>
          <button className="doc-btn" onClick={handleDocumentOptionClick}>문서 추가하기</button>
        </div> */}

        {/* 숨겨진 파일 입력 필드 */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
          accept=".pdf,.doc,.docx,.txt"
        />
      </div>

      {/* URL 입력창 */}
      {showUrlInput && (
      <div className="url-input-box-main">
        <input
          type="text"
          placeholder="URL을 입력하세요"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          className="url-input-main"
        />
        <button 
          onClick={() => {
            handleAddUrl();
            setShowUrlInput(false); // 입력 후 닫기
          }} 
          className="add-url-btn"
        >
          추가
        </button>
      </div>
      )}

      {/* 문서 추가 창 */}
      {selectedFile && (
        <div className="selected-file-container">
        <div className="selected-file">
          <img src="/assets/document.png" alt="파일" className="file-icon" />
          <span className="file-name">{selectedFile.name}</span>
          <button 
            className="file-cancel" 
            onClick={() => setSelectedFile(null)}
            title="파일 선택 취소"
          >
            ×
          </button>
        </div>
      </div>
      )}

      {addedUrls.length > 0 && (
        <div className="url-list">
          {addedUrls.map((url, index) => (
            <div key={index} className="selected-file-container">
              <div className="selected-file">
                <span className='url-icon'>🌐</span>
                <span>{url}</span>
                <button 
                  className="file-cancel"
                  onClick={() => {
                    const newUrls = [...addedUrls];
                    newUrls.splice(index, 1);
                    setAddedUrls(newUrls);
                  }}
                  title="URL 제거"
                >
                  ×
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}

export default MainPage;