import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from "lucide-react";

const ChatMessage = ({ qa, index, handleShowGraph }) => {
    // 현재 보고 있는 답변 타입 상태 (local 또는 global)
    const [currentAnswerType, setCurrentAnswerType] = useState('local');
    
    // 현재 보고 있는 답변 가져오기
    const getCurrentAnswer = () => {
        if (currentAnswerType === 'local') {
            return qa.localAnswer || qa.answer || "로컬 답변이 없습니다.";
        } else {
            return qa.globalAnswer || "글로벌 답변이 없습니다.";
        }
    };
    
    // 답변 타입 전환 함수
    const switchToLocal = () => {
        setCurrentAnswerType('local');
    };
    
    const switchToGlobal = () => {
        setCurrentAnswerType('global');
    };
    
    return (
        <div className="qa-box">
            <div className="question-box">{qa.question}</div>
            {qa.answer && (
                <div className="answer-box">
                    <div className="flex-row">
                        <div className="nav-button-container">
                            <button
                                type="button"
                                className={`nav-button ${currentAnswerType === 'global' ? 'active' : ''}`}
                                onClick={switchToLocal}
                                title="로컬 검색 결과 보기"
                            >
                                <ChevronLeft />
                            </button>
                            {currentAnswerType === 'global' && <span className="nav-text">Local</span>}
                        </div>
                        
                        <span className="answer-text">{getCurrentAnswer()}</span>
                        
                        <div className="nav-button-container">
                            <button
                                type="button"
                                className={`nav-button ${currentAnswerType === 'local' ? 'active' : ''}`}
                                onClick={switchToGlobal}
                                title="글로벌 검색 결과 보기"
                            >
                                <ChevronRight />
                            </button>
                            {currentAnswerType === 'local' && <span className="nav-text">Global</span>}
                        </div>
                    </div>
                    {qa.actionButtonVisible && (
                        <div className="action-button-container">
                            <button
                                type="button"
                                className="action-button-left"
                                onClick={(e) => handleShowGraph(e, index)}
                            >
                                <span className="button-icon">
                                    <img src="assets/graph.svg" alt="지식 그래프 아이콘" />
                                </span>
                                <div className="tooltip"><span className="tooltiptext">지식 그래프 보기</span></div>
                            </button>
                            <div className="action-button-right">
                                <span className="button-text">
                                    {currentAnswerType === 'local' ? qa.localConfidence || qa.confidence : qa.globalConfidence || 0}%
                                </span>
                                <div className="tooltip"><span className="tooltiptext">답변 정확도 보기</span></div>
                            </div>
                        </div>
                    )}
                </div>
            )}
            {qa.actionButtonVisible && qa.relatedQuestionsVisible && (
                <div className="relative-buttons">
                    <button type="button" className="question-button">관련 질문 추천 1</button>
                    <button type="button" className="question-button">관련 질문 추천 2</button>
                </div>
            )}
        </div>
    );
};

export default ChatMessage;