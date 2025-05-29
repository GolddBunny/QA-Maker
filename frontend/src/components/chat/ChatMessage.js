import React, { useState, useRef, useEffect } from 'react';
import { ChevronLeft, ChevronRight, FileText, ExternalLink } from "lucide-react";
import { marked } from 'marked';

const ChatMessage = ({ qa, index, handleShowGraph, showGraph, handleShowDocument, showDocument, sendQuestion, handleDownloadDocument }) => {
    // 현재 보고 있는 답변 타입 상태 (local 또는 global)
    const [currentAnswerType, setCurrentAnswerType] = useState('local');
    const [relatedQuestions, setRelatedQuestions] = useState([]);
    const [isLoadingRelated, setIsLoadingRelated] = useState(false);
    const [rating, setRating] = useState(0);
    const [selectedHeadlineIndex, setSelectedHeadlineIndex] = useState(null); // 선택된 문서 인덱스 추적
    const chatEndRef = useRef(null);
    
    // 현재 보고 있는 답변 가져오기
    const getCurrentAnswer = () => {
        if (currentAnswerType === 'local') {
            let answer = qa.localAnswer || qa.answer || "로컬 답변이 없습니다.";
                        
            // URL 버튼을 답변 텍스트에 삽입 (글로벌이 아닌 경우에만)
            if (qa.sources && qa.sources.length > 0) {
                // [Data: ...] 패턴 중에서 Sources가 포함된 것만 찾기
                const dataWithSourcesPattern = /\[Data: [^[\]]*Sources[^[\]]*\]/g;
                const hasDataWithSourcesPattern = dataWithSourcesPattern.test(answer);
                                
                // 패턴 검색을 위해 정규식 초기화 (test 후에는 lastIndex가 변경됨)
                dataWithSourcesPattern.lastIndex = 0;
                
                // 모든 소스에 대한 버튼 HTML 생성
                const createSourceButtons = (sources) => {
                    return sources.map(source => {
                        const buttonText = source.title || '출처 보기';
                        return source.url 
                            ? `<a href="${source.url}" target="_blank" rel="noopener noreferrer" class="source-link-button">${buttonText}</a>`
                            : `<span class="source-link-button disabled">${buttonText}</span>`;
                    }).join(' ');
                };
                                
                if (hasDataWithSourcesPattern) {
                    // [Data: ...Sources...] 패턴이 있는 경우, 해당 패턴 뒤에 모든 URL 버튼 추가
                    const allButtonsHtml = createSourceButtons(qa.sources);
                    
                    // Sources가 포함된 [Data: ...] 패턴과 그 뒤의 마침표를 찾아서 마침표 다음에 모든 URL 버튼 추가
                    answer = answer.replace(
                        /(\[Data: [^[\]]*Sources[^[\]]*\])(\s*\.)/g,
                        `$1$2 ${allButtonsHtml}`
                    );
                } else {
                    // Sources가 포함된 [Data: ...] 패턴이 없는 경우, 마지막 문장 끝에 모든 URL 버튼 추가
                    const sentencePattern = /[^.!?]+[.!?](?:\s|$)/g;
                    const sentences = [];
                    let match;
                                        
                    while ((match = sentencePattern.exec(answer)) !== null) {
                        sentences.push(match[0]);
                    }
                                        
                    if (sentences.length > 0) {
                        // 마지막 문장
                        const lastSentence = sentences[sentences.length - 1].trim();
                        
                        // 모든 소스에 대한 버튼 HTML 생성
                        const allButtonsHtml = createSourceButtons(qa.sources);
                        
                        const lastSentenceWithButtons = `${lastSentence} ${allButtonsHtml}`;
                                                        
                        // 마지막 문장을 모든 버튼이 포함된 문장으로 교체
                        answer = answer.substring(0, answer.lastIndexOf(lastSentence)) + lastSentenceWithButtons;
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
        
        let cleanAnswer = answer;
        
        // [Data: ...] 제거
        cleanAnswer = cleanAnswer.replace(/\[Data:[^\]]*\]/g, "");
        
        // INFO: ~ Response: 구간 제거 (줄바꿈 포함)
        cleanAnswer = cleanAnswer.replace(/INFO:([\s\S]*?)Response:/g, "");
        
        // 마크다운 헤딩 한단계씩 줄임
        cleanAnswer = cleanAnswer.replace(/^### /gm, "#### ");
        cleanAnswer = cleanAnswer.replace(/^## /gm, "### ");
        cleanAnswer = cleanAnswer.replace(/^# /gm, "## ");
        
        // Markdown → HTML 변환
        const htmlAnswer = marked.parse(cleanAnswer);
        
        return { __html: htmlAnswer };
    };

    // 특정 근거 문서 열기
    const handleHeadlineClick = (headline, headlineIndex) => {
        console.log('문서 클릭됨:', headline, headlineIndex);
        // 현재 선택된 headline 설정
        setSelectedHeadlineIndex(headlineIndex); // 클릭한 headline의 인덱스 저장
        
        // 클릭한 headline 문서 표시
        if (qa.headlines && qa.headlines.length > 0) {
            // handleShowDocument 함수에 인덱스와 특정 헤드라인 전달
            if (typeof handleShowDocument === 'function') {
                console.log('handleShowDocument 호출:', index, headline);
                handleShowDocument(index, headline);
            } else {
                console.error('handleShowDocument is not a function');
            }
        }
    };

    const getCurrentAccuracy = () => {
        if (currentAnswerType === 'local') {
            return qa.localConfidence !== null && qa.localConfidence !== undefined ? 
                qa.localConfidence.toFixed(1) : '계산중';
        } else {
            return qa.globalConfidence !== null && qa.globalConfidence !== undefined ? 
                qa.globalConfidence.toFixed(1) : '계산중';
        }
    };

    const scrollToBottom = () => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    };
    
    // 컴포넌트 초기화 시 props 체크, 선택된 항목 변경시 로컬 스토리지에 저장
    useEffect(() => {
        if (selectedHeadlineIndex !== null) {
            localStorage.setItem(`selected-headline-${index}`, selectedHeadlineIndex);
        }
    }, [selectedHeadlineIndex, index]);
    
    // 스크롤 처리
    useEffect(() => {
        scrollToBottom();
    }, [qa.question, qa.answer]);
    
    return (
        <div className="qa-box">
            <div className="question-box">{qa.question}</div>

            {qa.answer && (
                <>
                <div className="answer-and-action">
                    {/* 답변과 근거문서를 하나의 컨테이너로 묶음 */}
                    <div className="answer-docs-container">
                        <div className="answer-box">
                            <div className="flex-row">
                                <div className="nav-button-container">
                                    <button
                                    type="button"
                                    className={`nav-button ${currentAnswerType === 'local' ? 'active' : ''}`}
                                    onClick={switchToLocal}
                                    title="첫번째 검색 결과 보기"
                                    >
                                    <ChevronLeft strokeWidth={3} size={32} />
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
                                    <ChevronRight strokeWidth={3} size={32} />
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* 근거 문서 목록 박스 */}
                        {(qa.headlines && qa.headlines.length > 0) || qa.isDocumentLoading ? (
                            <div className="source-docs-container">
                                <div className="source-docs-header">
                                    <span>📄 근거 문서 목록</span>
                                </div>
                                
                                {qa.isDocumentLoading ? (
                                    <div className="source-docs-loading">로딩 중...</div>
                                ) : (
                                    <div className="source-docs-list">
                                    {qa.headlines && qa.headlines.length > 0 ? (
                                        qa.headlines.map((headline, i) => (
                                        <div 
                                            key={i} 
                                            className={`source-doc-item ${selectedHeadlineIndex === i ? 'selected' : ''}`}
                                            onClick={() => handleHeadlineClick(headline, i)}
                                        >
                                            <span className="source-doc-title">
                                            {headline}
                                            </span>
                                            
                                            {/* 다운로드 버튼 */}
                                            <button className="download-button" title="원본 문서 다운"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDownloadDocument(headline);
                                            }}
                                            >
                                                <img 
                                                    src="/assets/download2.png" 
                                                    alt="다운로드" 
                                                />
                                            </button>
                                        </div>
                                        ))
                                    ) : (
                                        <div className="source-docs-empty">근거 문서가 없습니다.</div>
                                    )}
                                    </div>
                                )}
                            </div>
                        ) : null}
                    </div>

                    <div className="answer-side-panel">
                    {!showGraph && !showDocument && (
                        <div className="action-button-container">
                        <span className="action-button-left-graph">
                            정확도 {getCurrentAccuracy()}%
                        </span>
                        </div>
                    )}

                    {!showGraph && !showDocument && (
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
                    {!showGraph && !showDocument && (
                        <div className="graph-button-wrapper">
                            <button 
                                type="button" 
                                className="action-button-left" 
                                onClick={() => handleShowGraph(qa.id, index)}
                            >
                                <span className="button-icon">
                                    지식 그래프 보기 
                                    <img src="/assets/graph_button.png" alt="Graph icon" />
                                </span>
                            </button>
                        </div>
                    )}
                    {!showGraph && !showDocument && (
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
                </>
            )}
            <div ref={chatEndRef} />
        </div>
    );
};

export default ChatMessage;