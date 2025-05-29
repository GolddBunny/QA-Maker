import React, { useEffect, useState, useRef } from 'react';
import '../styles/ProgressingBar.css';

const ProgressingBar = ({ 
  onClose, 
  onAnalyzer, 
  isCompleted, 
  stepExecutionTimes = {}, 
  currentStep = 'crawling' 
}) => {
  const [progress, setProgress] = useState(0);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (isCompleted) {
      setProgress(100);
      return;
    }

    const stepConfigs = {
      crawling: { max: 25, interval: 3000 },
      structuring: { max: 50, interval: 5000 },
      document: { max: 75, interval: 6000 },
      indexing: { max: 99, interval: 15000 },
    };

    const config = stepConfigs[currentStep];

    if (config) {
      intervalRef.current = setInterval(() => {
        setProgress(prev => {
          if (prev >= config.max) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
            return prev;
          }

          const increment = Math.floor(Math.random() * 4) + 2;
          return Math.min(prev + increment, config.max);
        });
      }, config.interval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [currentStep, isCompleted]);

  const displayProgress = `${Math.min(progress, 100)}%`;

  // 단계별 상태를 결정하는 함수
  const getStepStatus = (stepName) => {
    const stepOrder = ['crawling', 'structuring', 'document', 'indexing'];
    const currentIndex = stepOrder.indexOf(currentStep);
    const stepIndex = stepOrder.indexOf(stepName);
    
    let executionTime = null;
    if (stepName === 'structuring') {
      const structuringTime = stepExecutionTimes.structuring || 0;
      const line1Time = stepExecutionTimes.line1 || 0;
      executionTime = structuringTime + line1Time;
      if (executionTime > 0) executionTime = Math.round(executionTime);
    }
    // indexing과 update 시간을 합쳐서 처리
    else if (stepName === 'indexing') {
      const indexingTime = stepExecutionTimes.indexing || 0;
      const updateTime = stepExecutionTimes.update || 0;
      executionTime = indexingTime + updateTime;
      if (executionTime > 0) executionTime = Math.round(executionTime);
    }
    // 다른 단계들은 기존 로직 유지
    else {
      executionTime = stepExecutionTimes[stepName];
    }
    
    if (executionTime !== null && executionTime > 0) {
      return 'completed';
    } else if (stepIndex === currentIndex) {
      return 'active';
    } else if (stepIndex < currentIndex) {
      return 'completed';
    } else {
      return 'waiting';
    }
  };

  // 단계별 표시 텍스트를 생성하는 함수
  const getStepText = (stepName, displayName) => {
    const status = getStepStatus(stepName);
    let executionTime = null;
    
    // structuring과 line1 시간을 합쳐서 처리
    if (stepName === 'structuring') {
      const structuringTime = stepExecutionTimes.structuring || 0;
      const line1Time = stepExecutionTimes.line1 || 0;
      executionTime = structuringTime + line1Time;
      if (executionTime > 0) executionTime = Math.round(executionTime);
    }
    // indexing과 update 시간을 합쳐서 처리
    else if (stepName === 'indexing') {
      const indexingTime = stepExecutionTimes.indexing || 0;
      const updateTime = stepExecutionTimes.update || 0;
      executionTime = indexingTime + updateTime;
      if (executionTime > 0) executionTime = Math.round(executionTime);
    }
    // 다른 단계들은 기존 로직 유지
    else {
      executionTime = stepExecutionTimes[stepName];
    }
    
    switch (status) {
      case 'completed':
        return `${displayName}<br /><span class="status-progress">완료 </span>`;
      case 'active':
        return `${displayName}<br /><span class="status-progress">진행 중 </span>`;
      case 'waiting':
      default:
        return `${displayName}<br /><span class="status-progress">대기중 </span>`;
    }
  };

  // 단계별 circle 클래스를 결정하는 함수
  const getCircleClass = (stepName) => {
    const status = getStepStatus(stepName);
    switch (status) {
      case 'completed':
        return 'circle completed';
      case 'active':
        return 'circle active';
      case 'waiting':
      default:
        return 'circle';
    }
  };

  return (
    <div className="progress-wrapper">
      {isCompleted && (
      <button className="progress-close-button" onClick={onClose}>×</button>
    )}
      
      <h2 className="progress-title">한성대 Q&A 시스템 구축 중 ...</h2>
      <p className="progress-desc">
        크롤링은 사이트 크기를 사전에 알 수 없기 때문에 시간이 오래 걸릴 수 있습니다.
      </p>

      <div className="progress-cards">
        <div className="progress-card">
          <div className="card-title">예상 완료 시간</div>
          <div className="card-value">약 10분</div>
        </div>
        <div className="progress-card">
          <div className="card-title">현재 진행률</div>
          <div className="card-value">
            {displayProgress}
          </div>
        </div>
      </div>

      <div className="progress-steps">
        <div className="step">
          <div className={getCircleClass('crawling')}>1</div>
          <div 
            className="step-desc"
            dangerouslySetInnerHTML={{
              __html: getStepText('crawling', 'URL Crawling')
            }}
          />
        </div>
        <div className="step">
          <div className={getCircleClass('structuring')}>2</div>
          <div 
            className="step-desc"
            dangerouslySetInnerHTML={{
              __html: getStepText('structuring', 'Web Structuring')
            }}
          />
        </div>
        <div className="step">
          <div className={getCircleClass('document')}>3</div>
          <div 
            className="step-desc"
            dangerouslySetInnerHTML={{
              __html: getStepText('document', 'Document Structuring')
            }}
          />
        </div>
        <div className="step">
          <div className={getCircleClass('indexing')}>4</div>
          <div 
            className="step-desc"
            dangerouslySetInnerHTML={{
              __html: getStepText('indexing', 'build KonwledgeGraph')
            }}
          />
        </div>
      </div>

      {/* <div className="progress-stats">
        <span>수집된 웹 페이지 수: ---</span>
        <span>수집된 문서 수: ---</span>
      </div> */}

      {isCompleted && (
        <div className="apply-btn-row" style={{ marginTop: '40px' }}>
          <button className="btn-apply-update" onClick={onAnalyzer}>
            Go to Analyzer
          </button>
        </div>
      )}
    </div>
  );
};

export default ProgressingBar;