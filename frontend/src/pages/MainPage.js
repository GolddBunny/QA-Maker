import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/MainPage.css";
import Sidebar from "../components/navigation/Sidebar";
import { usePageContext } from '../utils/PageContext';

function MainPage() {
  const { currentPageId, setCurrentPageId } = usePageContext(); 
  const [message, setMessage] = useState('');
  const [isDropdownVisible, setIsDropdownVisible] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [searchType, setSearchType] = useState('url');
  const [selectedFile, setSelectedFile] = useState(null);

  const navigate = useNavigate(); // 페이지 이동을 위한 useNavigate
  const location = useLocation();
  const fileInputRef = useRef(null);

  const [urlInput, setUrlInput] = useState('');
  const [addedUrls, setAddedUrls] = useState([]);
  const [showUrlInput, setShowUrlInput] = useState(false);

  useEffect(() => {
    // 로컬 스토리지에서 페이지 목록 불러오기
    const savedPages = JSON.parse(localStorage.getItem('pages')) || [];
    // "기본 페이지" 찾기
    const defaultPage = savedPages.find(page => page.type === "main");
    // "기본 페이지"가 존재하면 해당 ID를 기본 페이지 ID로 설정
    if (defaultPage) {
        setCurrentPageId(defaultPage.id);
        localStorage.setItem('currentPageId', defaultPage.id);
        console.log("기본 페이지 ID 설정:", defaultPage.id);
    } else {
        console.log("기본 페이지를 찾을 수 없습니다.");
    }
  }, [setCurrentPageId]);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

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

  const headerText = "무엇이든 물어보세요!";
  const headerLetters = headerText.split('');
  
  return (
    <div className={`container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      <Sidebar isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />

      {/* 상단 버튼 추가 */}
      <div className="top-buttons">
        <div>
          <button className="top-button">
            🌐
          </button>
          <div className="stats">URL 수<br />43231</div>
        </div>
        <div>
          <button className="top-button">
            📑
          </button>
          <div className="stats">문서 수<br />5308</div>
        </div>
        <div>
          <button className="top-button">
            🙆🏻‍♀️
          </button>
          <div className="stats">엔티티 수<br />328</div>
        </div>
      </div>

      {/* 제목 애니메이션 */}
      <h1>
        {headerLetters.map((letter, index) => (
          <span key={index}>
            {letter === ' ' ? '\u00A0' : letter}
          </span>
        ))}
      </h1>

      <div className="typing-text">
        한성대학교 홈페이지에서 찾아볼게요!
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

        <div className="bottom-left-buttons">
          <button className="url-btn" onClick={handleUrlOptionClick}>URL 추가하기</button>
          <button className="doc-btn" onClick={handleDocumentOptionClick}>문서 추가하기</button>
        </div>

        {/* 숨겨진 파일 입력 필드 */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
          accept=".pdf,.doc,.docx,.txt"
        />
      </div>

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