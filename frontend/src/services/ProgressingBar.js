import React, { useEffect, useState, useRef } from 'react';
import '../styles/ProgressingBar.css';

const ProgressingBar = ({
  onClose, 
  onAnalyzer, 
  isCompleted, 
  stepExecutionTimes = {}, 
  currentStep = 'crawling',
  estimatedTime = null
}) => {
  const [progress, setProgress] = useState(0);
  const [displayProgress, setDisplayProgress] = useState(0);
  const [showAnalyzerButton, setShowAnalyzerButton] = useState(false);
  const intervalRef = useRef(null);
  const displayIntervalRef = useRef(null);

  // 진행률 애니메이션
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // 각 단계별 진행률 증가 한계치
    const stepConfigs = {
      crawling: { max: 12 },      // 24%까지
      structuring: { max: 30 },   // 53%까지
      document: { max: 48 },      // 65%까지
      indexing: { max: 99 },      // 99%까지
    };

    const config = stepConfigs[currentStep];

    if (config) {
      const updateProgress = () => {
        setProgress(prev => {
          if (prev >= config.max) {
            return prev;
          }

          // 랜덤한 동작 패턴 결정
          const randomAction = Math.random();
          
          // 50% 확률로 멈춤
          if (randomAction < 0.5) {
            return prev;
          }
          // 10% 확률로 빠른 진행
          else if (randomAction < 0.6) {
            const fastIncrement = Math.floor(Math.random() * 4) + 1; // 1~4% 증가
            return Math.min(prev + fastIncrement, config.max);
          }
          // 40% 확률로 일반 진행
          else {
            const normalIncrement = Math.floor(Math.random() * 2) + 1; // 1~2% 증가
            return Math.min(prev + normalIncrement, config.max);
          }
        });

        // 다음 업데이트까지의 랜덤 시간 설정 (4000ms ~ 12000ms)
        const nextDelay = Math.floor(Math.random() * 8000) + 4000;
        
        setTimeout(() => {
          updateProgress();
        }, nextDelay);
      };

      // 첫 업데이트 시작 (더 긴 초기 딜레이)
      const initialDelay = Math.floor(Math.random() * 3000) + 2000;
      setTimeout(() => {
        updateProgress();
      }, initialDelay);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [currentStep, isCompleted]);

  // 표시되는 진행률을 부드럽게 애니메이션
  useEffect(() => {
    if (displayIntervalRef.current) {
      clearInterval(displayIntervalRef.current);
    }

    displayIntervalRef.current = setInterval(() => {
      setDisplayProgress(prev => {
        if (prev === progress) {
          clearInterval(displayIntervalRef.current);
          return prev;
        }
        
        const diff = progress - prev;
        if (Math.abs(diff) <= 1) {
          clearInterval(displayIntervalRef.current);
          return progress;
        }
        
        // 부드러운 증가/감소
        const increment = diff > 0 ? Math.ceil(diff / 10) : Math.floor(diff / 10);
        return prev + increment;
      });
    }, 100); // 더 느린 애니메이션을 위해 간격 늘림

    return () => {
      if (displayIntervalRef.current) {
        clearInterval(displayIntervalRef.current);
      }
    };
  }, [progress]);

  // 완료 후 10초 후에 progress와 displayProgress를 100%로 설정하고 버튼 표시
  useEffect(() => {
    let timeoutId;
    if (isCompleted && currentStep === 'indexing') {
      const indexingTime = stepExecutionTimes.indexing || 0;
      const updateTime = stepExecutionTimes.update || 0;
      const indexingCompleted = indexingTime + updateTime > 0;

      if (indexingCompleted) {
        setShowAnalyzerButton(false);
        timeoutId = setTimeout(() => {
          setProgress(100);
          setDisplayProgress(100);
          setShowAnalyzerButton(true);
        }, 10000);
      }
    } else {
      setShowAnalyzerButton(false);
    }

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [isCompleted, currentStep, stepExecutionTimes]);

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

  // 예상 완료 시간 표시 텍스트 결정
  const getEstimatedTimeText = () => {
    if (estimatedTime && estimatedTime.formattedTime) {
      return estimatedTime.formattedTime;
    }
    return "10분"; // 기본값
  };

  return (
    <div className="progress-wrapper">
      {/* 완료 시 닫기 버튼 노출 */}
      {isCompleted && (
        <button className="progress-close-button" onClick={onClose}>×</button>
      )}
      
      <h2 className="progress-title">시스템 구축 중 ...</h2>
      <p className="progress-desc">
        크롤링은 사이트 크기를 사전에 알 수 없기 때문에 시간이 오래 걸릴 수 있습니다.
      </p>

      {/* 진행률 카드 (예상 완료 시간, 현재 진행률) */}
      <div className="progress-cards">
        <div className="progress-card">
          <div className="card-title">예상 완료 시간</div>
          <div className="card-value">{getEstimatedTimeText()}</div>
        </div>
        <div className="progress-card">
          <div className="card-title">현재 진행률</div>
          <div className="card-value">
            {Math.min(displayProgress, 100)}%
          </div>
        </div>
      </div>

      {/* 단계별 진행 상태 */}
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
              __html: getStepText('indexing', 'build KnowledgeGraph')
            }}
          />
        </div>
      </div>
      
      {/* 완료 후 10초 대기 후 이동 버튼 노출 */}
      {showAnalyzerButton && (
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