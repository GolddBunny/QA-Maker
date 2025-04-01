import React from 'react';
import { ChevronLeft, ChevronRight } from "lucide-react";

const ChatMessage = ({ qa, index, handleShowGraph }) => {
    return (
        <div className="qa-box">
            <div className="question-box">{qa.question}</div>
            {qa.answer && (
                <div className="answer-box">
                    <div className="flex-row">
                        <button type="button" className="nav-button"><ChevronLeft /></button>
                        <span className="answer-text">{qa.answer}</span>
                        <button type="button" className="nav-button"><ChevronRight /></button>
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
                                <span className="button-text">{qa.confidence}%</span>
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