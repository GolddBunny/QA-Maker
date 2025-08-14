import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MoreHorizontal, Smile } from 'lucide-react';
import { useQAHistoryContext } from '../utils/QAHistoryContext';
import "../styles/UserDashBoard.css";

const UserDashboard = () => {
  const navigate = useNavigate();
  const { pageId } = useParams();
  
  const [qaData, setQaData] = useState([]);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [averageSatisfaction, setAverageSatisfaction] = useState(0);

  // Firebase QA History Context 사용 (pageId 기반)
  const { 
    qaHistory, 
    loading: qaLoading, 
    error: qaError 
  } = useQAHistoryContext(pageId, true);
  
  useEffect(() => {
    if (!pageId) {
      console.error("PageId가 없습니다.");
      return;
    }

    console.log("UserDashboard pageId:", pageId);
    console.log("QA History:", qaHistory);

    if (qaHistory && qaHistory.length > 0) {
      // 특정 pageId의 데이터만 필터링 (혹시 Firebase에서 필터링이 안 되었을 경우를 대비)
      const filteredQAHistory = qaHistory.filter(qa => 
        qa.pageId === pageId || qa.pageId === String(pageId)
      );
      
      console.log("Filtered QA History for pageId:", pageId, filteredQAHistory);

      // QA History 데이터를 qaData 형식으로 변환
      const processedData = filteredQAHistory.map(qa => {
        // conversations 배열에서 첫 번째 conversation 가져오기
        const firstConversation = qa.conversations && qa.conversations.length > 0 
          ? qa.conversations[0] 
          : {};

        return {
          id: qa.id,
          question: qa.question,
          conversations: qa.conversations || [],
          // 직접 접근 가능하도록 추가
          satisfaction: firstConversation.satisfaction || 0,
          confidence: firstConversation.confidence || firstConversation.globalConfidence || 0
        };
      });

      setQaData(processedData);
      setTotalQuestions(processedData.length);
      
      // 평균 만족도 계산
      const satisfactionValues = processedData
        .map(qa => qa.satisfaction)
        .filter(satisfaction => satisfaction > 0); // 0보다 큰 값만 계산에 포함
      
      const avgSatisfaction = satisfactionValues.length > 0 
        ? (satisfactionValues.reduce((sum, satisfaction) => sum + satisfaction, 0) / satisfactionValues.length)
        : 0;
      
      setAverageSatisfaction(avgSatisfaction.toFixed(1));
    } else {
      // 데이터가 없을 때 초기화
      console.log("해당 pageId의 QA 데이터가 없습니다:", pageId);
      setQaData([]);
      setTotalQuestions(0);
      setAverageSatisfaction(0);
    }
  }, [pageId, qaHistory]);

  const handleBack = () => {
    navigate(`/admin/${pageId}`);
  };

  // 별점 렌더링 함수
  const renderStars = (rating) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 !== 0;
    
    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        stars.push(
          <span key={i} className="star star-filled">★</span>
        );
      } else if (i === fullStars && hasHalfStar) {
        stars.push(
          <span key={i} className="star star-filled">☆</span>
        );
      } else {
        stars.push(
          <span key={i} className="star star-empty">☆</span>
        );
      }
    }
    
    return stars;
  };

  // 신뢰도 진행바 렌더링
  const renderConfidenceBar = (confidence) => {
    // confidence 값의 범위를 확인하여 적절히 처리
    let percentage;
    
    if (confidence <= 1) {
      // 0-1 사이의 소수점 값인 경우 (예: 0.899)
      percentage = Math.round(confidence * 100);
    } else if (confidence <= 100) {
      // 이미 0-100 사이의 값인 경우 (예: 89.9)
      percentage = Math.round(confidence);
    } else {
      // 100보다 큰 값인 경우 (잘못된 데이터)
      percentage = Math.min(Math.round(confidence / 10), 100); // 임시 보정
    }
    
    return (
      <div className="confidence-bar-wrapper">
        <div className="confidence-bar">
          <div 
            className="confidence-progress"
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
        <span className="confidence-percentage">{percentage}%</span>
      </div>
    );
  };

  console.log("렌더링 중... qaData:", qaData);

  // 로딩 중일 때
  if (qaLoading) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-content">
          <div className="dashboard-header">
            <div className="header-controls">
              <button className="back-button" onClick={handleBack}>
                ← 뒤로가기
              </button>
              <h1 className="main-title">사용자 만족도</h1>
            </div>
          </div>
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            페이지 ID {pageId}의 데이터를 불러오는 중...
          </div>
        </div>
      </div>
    );
  }

  // 에러가 있을 때
  if (qaError) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-content">
          <div className="dashboard-header">
            <div className="header-controls">
              <button className="back-button" onClick={handleBack}>
                ← 뒤로가기
              </button>
              <h1 className="main-title">사용자 만족도</h1>
            </div>
          </div>
          <div style={{ textAlign: 'center', padding: '2rem', color: 'red' }}>
            페이지 ID {pageId}의 데이터 로드 중 오류가 발생했습니다: {qaError}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-content">
        {/* 헤더 */}
        <div className="dashboard-header">
          <div className="header-controls">
            <button className="back-button" onClick={handleBack}>
              ← 뒤로가기
            </button>
            <h1 className="main-title">사용자 만족도 (Page ID: {pageId})</h1>
          </div>
        </div>

        {/* 통계 카드 */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-card-content">
              <div className="stat-info">
                <h3 className="stat-title">🧾 사용자 질문 수</h3>
                <p className="stat-value">{totalQuestions.toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-card-content">
              <div className="stat-info">
                <h3 className="stat-title">⭐️ 평균 만족도</h3>
                <p className="stat-value">{averageSatisfaction} / 5</p>
              </div>
            </div>
          </div>
        </div>

        {/* 유저 질문 및 만족도 분석 */}
        <div className="analysis-section">
          <div className="analysis-header">
            <h2 className="analysis-title">🙋🏻‍♀️ 유저 질문 및 만족도 분석</h2>
            <p className="analysis-subtitle">*정보 신뢰성: 제공된 정보의 정확성 평가</p>
          </div>

          <div className="table-container">
            {/* 테이블 헤더 */}
            <div className="table-header">
              <div className="table-cell question-header">질문</div>
              <div className="table-cell satisfaction-header">만족도</div>
              <div className="table-cell confidence-header">정보 신뢰성</div>
            </div>

            {/* 테이블 내용 */}
            <div className="table-body">
              {qaData.length === 0 ? (
                <div className="table-row">
                  <div className="table-cell" style={{ textAlign: 'center', padding: '2rem', gridColumn: '1 / -1' }}>
                    페이지 ID {pageId}에 대한 QA 데이터가 없습니다.
                  </div>
                </div>
              ) : (
                qaData.map((qa, index) => {
                  const satisfaction = qa.satisfaction || 0;
                  const confidence = qa.confidence || 0;
                  
                  return (
                    <div key={qa.id || index} className="table-row">
                      {/* 질문 */}
                      <div className="table-cell question-cell">
                        <p className="question-text">{qa.question || '질문 없음'}</p>
                      </div>
                      
                      {/* 만족도 */}
                      <div className="table-cell satisfaction-cell">
                        <div className="stars-wrapper">
                          {renderStars(satisfaction)}
                        </div>
                        <p className="satisfaction-value">({satisfaction})</p>
                      </div>
                      
                      {/* 정보 신뢰성 */}
                      <div className="table-cell confidence-cell">
                        {renderConfidenceBar(confidence)}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserDashboard;