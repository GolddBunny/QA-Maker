// ProgressingBar.js
import React from 'react';
import '../styles/ProgressingBar.css';

const ProgressingBar = () => {
  return (
    <div className="progress-wrapper">
      <h2 className="progress-title">한성대 Q&A 시스템 구축 중 ...</h2>
      <p className="progress-desc">
        크롤링은 사이트 크기를 사전에 알 수 없기 때문에 시간이 오래 걸릴 수 있습니다.
      </p>

      <div className="progress-cards">
        <div className="progress-card">
          <div className="card-title">예상 완료 시간</div>
          <div className="card-value">약 45분</div>
        </div>
        <div className="progress-card">
          <div className="card-title">현재 진행률</div>
          <div className="card-value">37%</div>
        </div>
      </div>

      <div className="progress-steps">
        <div className="step">
          <div className="circle">1</div>
          <div className="step-desc">crawling<br /><span className="status">완료 (12분)</span></div>
        </div>
        <div className="step">
          <div className="circle active">2</div>
          <div className="step-desc">web structuring<br /><span className="status">진행 중 (약 5분 남음)</span></div>
        </div>
        <div className="step">
          <div className="circle">3</div>
          <div className="step-desc">document structuring<br /><span className="status">대기중 (~30분)</span></div>
        </div>
        <div className="step">
          <div className="circle">4</div>
          <div className="step-desc">indexing<br /><span className="status">대기중 (~30분)</span></div>
        </div>
      </div>

      <div className="progress-stats">
        <span>수집된 웹 페이지 수: ---</span>
        <span>수집된 문서 수: ---</span>
      </div>
    </div>
  );
};

export default ProgressingBar;
