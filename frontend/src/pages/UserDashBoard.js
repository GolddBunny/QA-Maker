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
      // 특정 pageId의 데이터만 필터링 (Firebase에서 필터링이 안 되었을 경우 대비)
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
          <span key={i} className="user-star user-star-filled">★</span>
        );
      } else if (i === fullStars && hasHalfStar) {
        stars.push(
          <span key={i} className="user-star user-star-filled">☆</span>
        );
      } else {
        stars.push(
          <span key={i} className="user-star user-star-empty">☆</span>
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
      // 0-1 사이의 소수점 값인 경우
      percentage = Math.round(confidence * 100);
    } else if (confidence <= 100) {
      // 이미 0-100 사이의 값인 경우
      percentage = Math.round(confidence);
    } else {
      // 100보다 큰 값인 경우 (잘못된 데이터)
      percentage = Math.min(Math.round(confidence / 10), 100);
    }
    
    return (
      <div className="user-confidence-bar-wrapper">
        <div className="user-confidence-bar">
          <div 
            className="user-confidence-progress"
            style={{ width: `${percentage}%` }}
          ></div>
        </div>
        <span className="user-confidence-percentage">{percentage}%</span>
      </div>
    );
  };

  console.log("렌더링 중... qaData:", qaData);

  // 로딩 중일 때
  if (qaLoading) {
    return (
      <div className="user-dashboard-container">
        <div className="user-dashboard-content">
          <div className="user-dashboard-header">
            <div className="user-header-controls">
              <button className="user-back-button" onClick={handleBack}>
                ← 뒤로가기
              </button>
              <h1 className="user-main-title">사용자 만족도</h1>
            </div>
          </div>
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            데이터를 불러오는 중...
          </div>
        </div>
      </div>
    );
  }

  // 에러가 있을 때
  if (qaError) {
    return (
      <div className="user-dashboard-container">
        <div className="user-dashboard-content">
          <div className="user-dashboard-header">
            <div className="user-header-controls">
              <button className="user-back-button" onClick={handleBack}>
                ← 뒤로가기
              </button>
              <h1 className="user-main-title">사용자 만족도</h1>
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
    <div className="user-dashboard-container">
      <div className="user-dashboard-content">
        {/* 헤더 */}
        <div className="user-dashboard-header">
          <div className="user-header-controls">
            <button className="user-back-button" onClick={handleBack}>
              ← 뒤로가기
            </button>
            <h1 className="user-main-title">사용자 만족도</h1>
          </div>
        </div>

        {/* 통계 카드 */}
        <div className="user-stats-grid">
          <div className="user-stat-card">
            <div className="user-stat-card-content">
              <div className="user-stat-info">
                <h3 className="user-stat-title">🧾 사용자 질문 수</h3>
                <p className="user-stat-value">{totalQuestions.toLocaleString()}</p>
              </div>
            </div>
          </div>

          <div className="user-stat-card">
            <div className="user-stat-card-content">
              <div className="user-stat-info">
                <h3 className="user-stat-title">⭐️ 평균 만족도</h3>
                <p className="user-stat-value">{averageSatisfaction} / 5</p>
              </div>
            </div>
          </div>
        </div>

        {/* 유저 질문 및 만족도 분석 */}
        <div className="user-analysis-section">
          <div className="user-analysis-header">
            <h2 className="user-analysis-title">🙋🏻‍♀️ 유저 질문 및 만족도 분석</h2>
            <p className="user-analysis-subtitle">*정보 신뢰성: 제공된 정보의 정확성 평가</p>
          </div>

          <div className="user-table-container">
            {/* 테이블 헤더 */}
            <div className="user-table-header">
              <div className="user-table-cell user-question-header">질문</div>
              <div className="user-table-cell user-satisfaction-header">만족도</div>
              <div className="user-table-cell user-confidence-header">정보 신뢰성</div>
            </div>

            {/* 테이블 내용 */}
            <div className="user-table-body">
              {qaData.length === 0 ? (
                <div className="user-table-row">
                  <div className="user-table-cell" style={{ textAlign: 'center', padding: '2rem', gridColumn: '1 / -1' }}>
                    현재 유저 질문이 없습니다.
                  </div>
                </div>
              ) : (
                qaData.map((qa, index) => {
                  const satisfaction = qa.satisfaction || 0;
                  const confidence = qa.confidence || 0;
                  
                  return (
                    <div key={qa.id || index} className="user-table-row">
                      {/* 질문 */}
                      <div className="user-table-cell user-question-cell">
                        <p className="user-question-text">{qa.question || '질문 없음'}</p>
                      </div>
                      
                      {/* 만족도 */}
                      <div className="user-table-cell user-satisfaction-cell">
                        <div className="user-stars-wrapper">
                          {renderStars(satisfaction)}
                        </div>
                        <p className="user-satisfaction-value">({satisfaction})</p>
                      </div>
                      
                      {/* 정보 신뢰성 */}
                      <div className="user-table-cell user-confidence-cell">
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