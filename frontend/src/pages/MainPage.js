import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/App.css";
import Sidebar from "../components/navigation/Sidebar";

function MainPage() {
  const [message, setMessage] = useState('');
  const [isRecentQuestionsVisible, setIsRecentQuestionsVisible] = useState(false);
  const [isDropdownVisible, setIsDropdownVisible] = useState(false);
  const [isPlusIconRotated, setIsPlusIconRotated] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  
  const navigate = useNavigate(); // 페이지 이동을 위한 useNavigate
  const location = useLocation();

  const toggleRecentQuestions = () => {
    setIsRecentQuestionsVisible(!isRecentQuestionsVisible);
  };
  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const toggleDropdown = () => {
    setIsPlusIconRotated(!isPlusIconRotated);
    setIsDropdownVisible(!isDropdownVisible);
  };

  const handleSearch = (e) => {
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
            <select>
              <option value="file">파일</option>
              <option value="document">문서</option>
            </select>
          </div>
        )}
      </div>

      <div className="recent-questions">
        <div className="recent-header">
          <button className="toggle-recent" onClick={toggleRecentQuestions}>
            <img
              src="/assets/triangle.png"
              alt="토글"
              className="icon"
            />
            <span>최근에 했던 질문</span>
          </button>
          <a href="view_all" className="view-all">
            view all →
          </a>
        </div>
        {isRecentQuestionsVisible && (
          <div className="question-list">
            <div className="question">
              나 110학점 들었는데, 졸업하려면 몇 학점 더 채워야 해?
            </div>
            <div className="question">
              신규 교과목 개설 절차와 필요한 서류는 무엇인가요?
            </div>
            <div className="question">운영체제란 무엇인가요?</div>
            <div className="question">리눅스에 대해 간략하게 설명해주세요.</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default MainPage;