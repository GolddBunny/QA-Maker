import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight,FileText, ExternalLink } from "lucide-react";

const ChatMessage = ({ qa, index, handleShowGraph, showGraph, handleShowDocument, showDocument, sendQuestion }) => {
    // 현재 보고 있는 답변 타입 상태 (local 또는 global)
    const [currentAnswerType, setCurrentAnswerType] = useState('local');
    const [relatedQuestions, setRelatedQuestions] = useState([]);
    const [isLoadingRelated, setIsLoadingRelated] = useState(false);
    const[rating, setRating] = useState(0);
    const chatEndRef = useRef(null);
    // 현재 보고 있는 답변 가져오기
    const getCurrentAnswer = () => {
        if (currentAnswerType === 'local') {
            let answer = qa.localAnswer || qa.answer || "로컬 답변이 없습니다.";
            
            // URL을 답변 텍스트에 삽입 (글로벌이 아닌 경우에만)
            if (qa.sources && qa.sources.length > 0) {
                // [Data: ...] 패턴 찾기
                const dataPattern = /\[Data: [^\]]+\]/g;
                const hasDataPattern = dataPattern.test(answer);
                
                // 패턴 검색을 위해 정규식 초기화 (test 후에는 lastIndex가 변경됨)
                dataPattern.lastIndex = 0;
                
                if (hasDataPattern) {
                    // [Data: ...] 패턴이 있는 경우, 패턴을 제외한 문장에만 링크 적용
                    const dataMatches = answer.match(dataPattern);
                    
                    if (dataMatches && dataMatches.length > 0 && qa.sources && qa.sources[0]) {
                        // [Data: ...] 패턴이 포함된 문장 찾기
                        const sentencePattern = /([^.!?]+)(\[Data:[^\]]+\])([^.!?]*[.!?])/g;
                        let result = answer;
                        let match;
                        
                        // 정규식을 사용하여 문장을 세 부분으로 나눔: 앞부분, [Data:...] 패턴, 뒷부분
                        while ((match = sentencePattern.exec(answer)) !== null) {
                            if (match.length >= 4) {
                                const beforeData = match[1]; // [Data:...] 패턴 앞 부분
                                const dataPattern = match[2]; // [Data:...] 패턴
                                const afterData = match[3]; // [Data:...] 패턴 뒤 부분
                                
                                // 원본 문장
                                const originalSentence = match[0];
                                
                                // 앞부분과 뒷부분만 링크를 적용한 새 문장
                                const linkedSentence = `<a href="${qa.sources[0].url}" target="_blank" rel="noopener noreferrer" class="inline-source-link">${beforeData}</a>${dataPattern}<a href="${qa.sources[0].url}" target="_blank" rel="noopener noreferrer" class="inline-source-link">${afterData}</a>`;
                                
                                // 원본 문장을 새 문장으로 교체
                                result = result.replace(originalSentence, linkedSentence);
                            }
                        }
                        
                        answer = result;
                    }
                } else {
                    // [Data: ...] 패턴이 없는 경우, 마지막 문장에 링크 추가 (기존 로직)
                    const sentencePattern = /[^.!?]+[.!?](?:\s|$)/g;
                    const sentences = [];
                    let match;
                    
                    while ((match = sentencePattern.exec(answer)) !== null) {
                        sentences.push(match[0]);
                    }
                    
                    if (sentences.length > 0) {
                        // 마지막 문장
                        const lastSentence = sentences[sentences.length - 1].trim();
                        
                        // 마지막 문장에 링크 추가
                        if (qa.sources[0]) {
                            const linkedSentence = `<a href="${qa.sources[0].url}" target="_blank" rel="noopener noreferrer" class="inline-source-link">${lastSentence}</a>`;
                            
                            // 마지막 문장을 링크된 문장으로 교체
                            answer = answer.substring(0, answer.lastIndexOf(lastSentence)) + linkedSentence;
                        }
                    }
                }
            }
            
            return answer;
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

    const wrapTextWithSpans = (text) => {
        return (
            <div className="bouncing-text">
                {text.split('').map((char, i) => (
                    <span key={i} style={{ animationDelay: `${i * 0.1}s` }}>
                        {char === ' ' ? '\u00A0' : char}
                    </span>
                ))}
            </div>
        );
    };

    // 답변이 로딩 중인지 확인하는 함수 
    const isLoadingAnswer = () => {
        const currentAnswer = currentAnswerType === 'local' 
            ? qa.localAnswer || qa.answer
            : qa.globalAnswer;
        
        return currentAnswer === "답변을 불러오는 중...";
    };

    // 답변 HTML로 렌더링하는 함수
    const renderAnswer = () => {
        const answer = getCurrentAnswer();
        
        // "답변을 불러오는 중..." 상태인 경우 바운스 애니메이션을 위해 null 반환
        if (answer === "답변을 불러오는 중...") {
            return null;
        }
        
        return { __html: answer };
    };

    const scrollToBottom = () => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    };
    useEffect(() => {
        scrollToBottom();
    }, [qa.question, qa.answer]);
    
    return (
        <div className="qa-box">
            <div className="question-box">{qa.question}</div>

            {qa.answer && (
                <>
                <div className="answer-and-action">
                    <div className="answer-box">
                        <div className="flex-row">
                            <div className="nav-button-container">
                                <button
                                type="button"
                                className={`nav-button ${currentAnswerType === 'local' ? 'active' : ''}`}
                                onClick={switchToLocal}
                                title="첫번째 검색 결과 보기"
                                >
                                <ChevronLeft />
                                </button>
                            </div>

                            <span className="answer-text">
                                {isLoadingAnswer() ? (
                                    wrapTextWithSpans("답변을 불러오는 중...")
                                ) : (
                                    <span dangerouslySetInnerHTML={renderAnswer()} />
                                )}
                            </span>

                            <div className="nav-button-container">
                                <button
                                type="button"
                                className={`nav-button ${currentAnswerType === 'global' ? 'active' : ''}`}
                                onClick={switchToGlobal}
                                title="두번째 검색 결과 보기"
                                >
                                <ChevronRight />
                                </button>
                            </div>
                        </div>
                    </div>

                    
                    <div className="answer-side-panel">
                    {!showGraph && (
                        <div className="action-button-container">
                        <span className="action-button-left">
                            정확도 {currentAnswerType === 'local' ? qa.localConfidence : qa.globalConfidence}%
                        </span>
                        </div>
                    )}

                    {!showGraph && (
                        <div className="graph-button-wrapper">
                        <button type="button" className="action-button-left" onClick={(e) => handleShowGraph(e, index, currentAnswerType)}>
                            <span className="button-icon">지식 그래프 보기 <img src="/assets/graph_button.png" alt="Graph icon" /></span>
                        </button>
                        </div>
                    )}

                    {!showGraph && (
                        <div className="satisfaction-button-container">
                        <button type="button" className="action-button-left">
                            <span className="button-icon">
                            만족도
                            <span className="rating-stars">
                                {[1, 2, 3, 4, 5].map((star) => (
                                <span
                                    key={star}
                                    className={`star ${rating >= star ? 'filled' : ''}`}
                                    onClick={() => setRating(star)}
                                >
                                    ★
                                </span>
                                ))}
                            </span>
                            </span>
                        </button>
                        </div>
                    )}

                    {qa.relatedQuestionsVisible && !showGraph && (
                        <div className="related-questions">
                            <div className="related-questions-header">💁🏻‍♀️ 관련 질문</div>
                            {isLoadingRelated ? (
                                <p className="loading">
                                    {wrapTextWithSpans("관련 질문 찾는 중")}
                                </p>
                            ) : (
                                <div className="related-questions-table">
                                    {Array.isArray(qa.relatedQuestions) && qa.relatedQuestions.length > 0 ? (
                                        qa.relatedQuestions.map((question, i) => (
                                            <div
                                                key={i}
                                                className="related-question-item"
                                                onClick={() => sendQuestion(question)}
                                                style={{ cursor: 'pointer' }}
                                            >
                                                {question}
                                            </div>
                                        ))
                                    ) : (
                                        <div className="related-question-item">관련 질문이 없습니다.</div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                    </div>
                </div>
                <button 
                    type="button" 
                    className={`source-docs-button ${showDocument ? 'active' : ''}`}
                    onClick={() => handleShowDocument(index)}
                >
                    <FileText size={14} className="mr-1" />
                    {qa.isDocumentLoading ? '로딩 중...' : '근거 문서'}
                </button>
                </>
            )}
            <div ref={chatEndRef} />
        </div>
    );
};

export default ChatMessage;