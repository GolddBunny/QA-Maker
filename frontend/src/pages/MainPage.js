import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/App.css";
import Sidebar from "../components/navigation/Sidebar";
import { usePageContext } from '../utils/PageContext';

function MainPage() {
  const { currentPageId, setCurrentPageId } = usePageContext(); 
  const [message, setMessage] = useState('');
  const [isDropdownVisible, setIsDropdownVisible] = useState(false);
  const [isPlusIconRotated, setIsPlusIconRotated] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [searchType, setSearchType] = useState('url');
  const [selectedFile, setSelectedFile] = useState(null);

  const navigate = useNavigate(); // 페이지 이동을 위한 useNavigate
  const location = useLocation();
  const fileInputRef = useRef(null);

  useEffect(() => {
    // 로컬 스토리지에서 페이지 목록 불러오기
    const savedPages = JSON.parse(localStorage.getItem('pages')) || [];
    // "기본 페이지" 찾기
    const defaultPage = savedPages.find(page => page.name === "기본 페이지");

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

  const toggleDropdown = () => {
    setIsPlusIconRotated(!isPlusIconRotated);
    setIsDropdownVisible(!isDropdownVisible);
  };

  const handleSearch = (e) => {
    e?.preventDefault();
    if (!message.trim() && !selectedFile) return;
    
    // 파일과 질문을 함께 전달
    const searchParams = new URLSearchParams();
    if (message.trim()) {
      searchParams.append('question', message.trim());
    }
    if (selectedFile) {
      // 파일 정보를 세션 스토리지에 저장하거나 
      // FormData를 사용하여 파일을 서버로 전송하는 로직을 여기에 추가할 수 있습니다.
      // 여기서는 간단하게 파일명을 URL 파라미터로 전달합니다.
      searchParams.append('file', selectedFile.name);
    }
    
    navigate(`/chat?${searchParams.toString()}`);
  };
  
  // Enter 키 처리 함수
  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSearch();
    }
  };

  // 선택박스에서 옵션 선택 시 처리하는 함수
  const handleOptionSelect = (type) => {
    setSearchType(type);
    setIsDropdownVisible(false);
    setIsPlusIconRotated(false);
    console.log(`${type} 선택됨`);
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
    setIsDropdownVisible(false);
    setIsPlusIconRotated(false);
    
    // 약간의 지연 후 파일 선택 다이얼로그 표시
    setTimeout(() => {
      fileInputRef.current.click();
    }, 50);
  };

  // URL 선택 시 처리
  const handleUrlOptionClick = () => {
    setSearchType('url');
    setIsDropdownVisible(false);
    setIsPlusIconRotated(false);
  };
  
  return (
    <div className={`container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
      <Sidebar isSidebarOpen={isSidebarOpen} toggleSidebar={toggleSidebar} />
      <h1>무엇이든 물어보세요!</h1>
      <p className="subtitle">한성대학교 홈페이지에서 찾아볼게요!</p>

      <div className="search-container">
        <button className="icon-btn" id="plus-btn" onClick={toggleDropdown}>
          <img
            src="/assets/add.png"
            alt="추가"
            className={`icon ${isPlusIconRotated ? "rotate" : ""}`}
            id="plus-icon"
          />
        </button>
        
        <input
          type="text"
          id="search-input"
          placeholder="질문을 입력하세요"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyPress}
        />
        
        <button className="icon-btn" onClick={handleSearch}>
          <img src="/assets/search.png" alt="검색" className="icon" />
        </button>
        
        {isDropdownVisible && (
          <div className="select-box">
            <div className="select-box-title">검색 유형</div>
            <button 
              className={`option-btn ${searchType === 'url' ? 'active' : ''}`}
              onClick={handleUrlOptionClick}
            >
              <img src="/assets/link.png" alt="URL" className="option-icon" />
              URL
            </button>
            <button 
              className={`option-btn ${searchType === 'document' ? 'active' : ''}`}
              onClick={handleDocumentOptionClick}
            >
              <img src="/assets/document.png" alt="문서" className="option-icon" />
              파일
            </button>
          </div>
        )}

        {/* 숨겨진 파일 입력 필드 */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
          accept=".pdf,.doc,.docx,.txt"
        />
      </div>

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
    </div>
  );
}

export default MainPage;