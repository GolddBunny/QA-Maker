import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/ChatPage.css";
import NetworkChart from "../components/charts/NetworkChart";
import ChatMessage from "../components/chat/ChatMessage";
import ChatInput from "../components/chat/ChatInput";
import { usePageContext } from "../utils/PageContext";
import { useQAHistoryContext } from "../utils/QAHistoryContext";
import Sidebar from "../components/navigation/Sidebar";
import Modal from '../components/modal/Modal';
import answerGraphData from '../json/answer_graphml_data.json';
const BASE_URL = 'http://localhost:5000/flask';

function ChatPage() {
    const { currentPageId, setCurrentPageId } = usePageContext();
    const { qaHistory, addQA, updateQAHeadlines, updateSelectedHeadline, updateQASources } = useQAHistoryContext();
    const [qaList, setQaList] = useState([]);
    const [newQuestion, setNewQuestion] = useState("");
    const [showGraph, setShowGraph] = useState(false);
    const [graphData, setGraphData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [serverResponseReceived, setServerResponseReceived] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const hasSentInitialQuestion = useRef(false);
    const [entities, setEntities] = useState("");
    const [relationships, setRelationships] = useState("");
    const [isSidebarOpen, setIsSidebarOpen] = useState(false); // 사이드바 상태
    // 그래프 데이터 캐시를 위한 참조
    const graphDataCacheRef = useRef({});
    
    // 근거 문서 관련 상태 추가
    const [showDocument, setShowDocument] = useState(false);
    const [headlines, setHeadlines] = useState([]); // 사용 가능 headline 목록
    const [headlinesLoading, setHeadlinesLoading] = useState(false); // headline 목록 로딩 상태
    const [selectedHeadline, setSelectedHeadline] = useState(''); // 선택된 headline 상태
    const [pdfUrl, setPdfUrl] = useState(''); // PDF URL 상태
    const [documentErrorMessage, setDocumentErrorMessage] = useState(''); // 문서 로드 오류 메시지
    const [currentMessageIndex, setCurrentMessageIndex] = useState(null); // 현재 선택된 메시지 인덱스
    const [currentQaId, setCurrentQaId] = useState(null); // 현재 QA ID 추가

    const chatEndRef = useRef(null);
    const [message, setMessage] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [urlInput, setUrlInput] = useState('');
    const [addedUrls, setAddedUrls] = useState([]);
    const [showUrlInput, setShowUrlInput] = useState(false);
    const [searchType, setSearchType] = useState('url');
    const [isDropdownVisible, setIsDropdownVisible] = useState(false);
    
    const fileInputRef = useRef(null);
    const { systemName } = usePageContext();

    const scrollToBottom = () => { //새 질문 시 아래로 스크롤
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    };

    // 모달 관련 상태 추가
    const [modalState, setModalState] = useState({
        isOpen: false,
        title: '',
        message: '',
        type: 'alert', // 'alert' 또는 'confirm'
        onConfirm: null
    });

    // 모달 함수들
    const showAlert = (title, message) => {
        setModalState({
            isOpen: true,
            title,
            message,
            type: 'alert',
            onConfirm: null
        });
    };

    const showConfirm = (title, message, onConfirm) => {
        setModalState({
            isOpen: true,
            title,
            message,
            type: 'confirm',
            onConfirm
        });
    };

    const closeModal = () => {
        setModalState({
            isOpen: false,
            title: '',
            message: '',
            type: 'alert',
            onConfirm: null
        });
    };

    const handleModalConfirm = () => {
        if (modalState.onConfirm) {
            modalState.onConfirm();
        }
        closeModal();
    };

    // 페이지 로드 시 초기 질문 또는 이전 대화 로드
    useEffect(() => {
        if (!currentPageId) {
            const storedPageId = localStorage.getItem("currentPageId");
            if (storedPageId) {
                // PageContext에 setCurrentPageId가 있다면 여기에 설정
                console.log("로컬스토리지에서 pageId 복원:", storedPageId);
                setCurrentPageId(storedPageId);
            }
        }
        scrollToBottom();
        const params = new URLSearchParams(location.search);
        const initialQuestion = params.get("question");
        const qaId = params.get("qaId");
        
        // 현재 QA ID 설정
        setCurrentQaId(qaId);
        
        // 이전 대화 로드 (qaId가 있는 경우)
        if (qaId) {
            loadPreviousQA(qaId);
        }
        // 새 질문 처리 (question 파라미터가 있는 경우)
        else if (initialQuestion && !hasSentInitialQuestion.current) {
            setNewQuestion(initialQuestion);
            setTimeout(() => {
                sendQuestion(initialQuestion);
            }, 500);
            hasSentInitialQuestion.current = true;
        }
    }, [location.search, currentPageId]);
    
    // 이전 대화 로드 함수
    const loadPreviousQA = (qaId) => {
        // qaHistory에서 해당 ID의 대화 찾기
        const qaItem = qaHistory.find(qa => qa.id === qaId);
        
        if (qaItem) {
            // 해당 대화의 모든 질문-답변 로드 (정확도와 관련 질문 포함)
            const conversationsWithDefaults = (qaItem.conversations || []).map(conversation => ({
                ...conversation,
                // 정확도 기본값 설정
                confidence: conversation.confidence || 0.0,
                localConfidence: conversation.localConfidence || 0.0,
                globalConfidence: conversation.globalConfidence || 0.0,
                // 관련 질문 기본값 설정
                relatedQuestions: conversation.relatedQuestions || [],
                relatedQuestionsVisible: conversation.relatedQuestionsVisible !== undefined 
                    ? conversation.relatedQuestionsVisible 
                    : (conversation.relatedQuestions && conversation.relatedQuestions.length > 0),
                // 기타 필드들 기본값
                headlines: conversation.headlines || [],
                sources: conversation.sources || [],
                actionButtonVisible: conversation.actionButtonVisible !== undefined ? conversation.actionButtonVisible : true,
            }));
            
            setQaList(conversationsWithDefaults);
            
            // 엔티티와 관계 정보 설정 (마지막 대화의 정보 사용)
            if (conversationsWithDefaults.length > 0) {
                const lastConversation = conversationsWithDefaults[conversationsWithDefaults.length - 1];
                setEntities(lastConversation.entities || "");
                setRelationships(lastConversation.relationships || "");
                setServerResponseReceived(true);
            }
        } else {
            // 해당 ID의 대화가 없으면 빈 배열로 초기화
            setQaList([]);
            setEntities("");
            setRelationships("");
            setServerResponseReceived(false);
        }
    };

    // 답변에서 소스 URL과 Title 추출 함수
    const extractSourcesFromAnswer = async (answerText, pageId) => {
        try {
            console.log("소스 추출 시작");
            
            // 예외 처리: 답변이 없거나 비어있을 경우
            if (!answerText || answerText.trim() === "") {
                console.log("답변이 비어있어 소스 추출을 건너뜁니다.");
                return [];
            }
            
            // 1. 우선 CSV에서 모든 URL 소스 추출 시도
            console.log("1. CSV에서 소스 추출 시도");
            const csvSources = await extractSourcesFromCSV();
            if (csvSources.length > 0) {
                console.log("CSV에서 소스 추출 성공:", csvSources);
                return csvSources;
            }
            
            // 2. CSV에서 추출 실패시 기존 방식(Sources 패턴) 시도
            console.log("2. 기존 Sources 패턴 방식으로 시도");
            if (!answerText.includes("Sources")) {
                console.log("Sources 표기가 없어 소스 추출을 건너뜁니다.");
                return [];
            }
            
            const response = await fetch(`${BASE_URL}/extract-sources`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    answer: answerText,
                    page_id: pageId
                })
            });
            
            if (!response.ok) {
                throw new Error(`서버 응답 오류: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                console.error("소스 추출 오류:", data.error);
                return [];
            }
            
            // 소스 데이터 검증
            if (!Array.isArray(data.sources)) {
                console.error("소스 데이터가 배열이 아닙니다:", data.sources);
                return [];
            }
            
            // 각 소스 데이터의 구조 검증
            const validSources = data.sources.filter(source => {
                if (!source || typeof source !== 'object') {
                    console.warn("유효하지 않은 소스 데이터:", source);
                    return false;
                }
                
                // URL과 title 중 하나는 있어야 함
                if (!source.url && !source.title) {
                    console.warn("URL/Title이 모두 없는 소스:", source);
                    return false;
                }
                
                console.log(`소스: Title="${source.title || '없음'}", URL="${source.url || '없음'}"`);
                return true;
            });
            
            console.log(`총 ${data.sources.length}개 소스 중 ${validSources.length}개 유효한 소스 추출됨`);
            return validSources;
            
        } catch (error) {
            console.error("소스 URL/Title 추출 실패:", error);
            return [];
        }
    };

    // CSV에서 직접 모든 URL 소스 추출하는 새로운 함수
    const extractSourcesFromCSV = async () => {
        try {
            console.log("CSV에서 소스 추출 시작");
            
            const response = await fetch(`${BASE_URL}/extract-sources-from-csv`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            });
            
            if (!response.ok) {
                throw new Error(`서버 응답 오류: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                console.error("CSV 소스 추출 오류:", data.error);
                return [];
            }
            
            console.log(`CSV에서 총 ${data.total_count}개의 소스 추출됨:`, data.sources);
            return data.sources || [];
            
        } catch (error) {
            console.error("CSV에서 소스 추출 실패:", error);
            return [];
        }
    };

    // 질문 전송 함수
    const sendQuestion = async (questionText) => {
        setIsLoading(true);
        setServerResponseReceived(false);

        const newQaEntry = { 
            question: questionText,
            answer: "답변을 불러오는 중...",
            localAnswer: "답변을 불러오는 중...",
            globalAnswer: "답변을 불러오는 중...",
            confidence: null,
            localConfidence: null,
            globalConfidence: null,
            actionButtonVisible: false, // 그래프 버튼 숨김
            relatedQuestionsVisible: false, // 관련 질문 숨김
            relatedQuestions: [], //관련 질문 배열
            headlines: headlines || [], // 근거 문서 목록
            selectedHeadline: headlines && headlines.length > 0 ? headlines[0] : '', // 기본 선택 근거 문서
            sources: [] // 소스 URL 정보
        };
        
        // 새 질문-답변 추가
        setQaList((prevQaList) => [...prevQaList, newQaEntry]);
        scrollToBottom();
        setNewQuestion(""); // 질문 입력란 초기화
        
        try {
            // URL과 문서 처리
            let additionalContext = questionText;
            
            // 문서 처리
            if (selectedFile) {
                try {
                    const formData = new FormData();
                    formData.append('file', selectedFile);

                    // 문서 처리 요청
                    const documentResponse = await fetch(`${BASE_URL}/process-document-direct`, {
                        method: "POST",
                        body: formData
                    });

                    const documentData = await documentResponse.json();
                    //console.log("문서 처리 결과:", documentData);

                    if (documentData.success && documentData.content) {
                        additionalContext += "\n아래는 답변에 참조할 문서 내용입니다. 반드시 아래 문서도 참조해서 답변을 해주세요.\n" + documentData.content + "\n\n";
                        //console.log(additionalContext);
                    } else {
                        console.warn("문서 내용이 비어 있거나 실패:", documentData.message);
                    }
                } catch (error) {
                    console.error("문서 처리 중 오류 발생:", error);
                }

                // 선택된 파일 초기화
                setSelectedFile(null);
            }

            // 각 방식별 서버 요청 함수
            const fetchLocalResponse = async () => {
                const response = await fetch(`${BASE_URL}/run-local-query`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({
                        page_id: currentPageId,
                        query: questionText
                    })
                });
                return await response.json();
            };
            
            const fetchGlobalResponse = () => {
                return fetch(`${BASE_URL}/run-global-query`, {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({
                        page_id: currentPageId,
                        query: questionText
                    })
                }).then(response => response.json());
            };
            
            // 사용된 근거 문서 목록 가져오기
            const fetchHeadlinesForAnswer = async () => {
                try {
                    const response = await fetch(`${BASE_URL}/api/context-sources?page_id=${currentPageId}`);
                    if (!response.ok) {
                        throw new Error(`서버 응답 오류: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    
                    return data.headlines || [];
                } catch (error) {
                    console.error("근거 문서 목록 가져오기 실패:", error);
                    return [];
                }
            };

            // 관련 질문 API 호출 함수
            const fetchRelatedQuestions = async () => {
                try {
                    const pageId = localStorage.getItem("currentPageId") || currentPageId;
                    if (!pageId || !questionText) {
                        console.log("페이지 ID 또는 질문 텍스트가 없음");
                        return [];
                    }

                    console.log("관련 질문 요청 시작:", pageId, questionText);
                    const response = await fetch(`${BASE_URL}/generate-related-questions`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ page_id: pageId, question: questionText })
                    });

                    console.log("관련 질문 응답 상태:", response.status);
                    
                    if (!response.ok) {
                        console.error("관련 질문 API 오류:", response.status);
                        return [];
                    }

                    const data = await response.json();
                    console.log("관련 질문 응답 데이터:", data);
                    
                    let questions = [];

                    if (typeof data.response === "string") {
                        questions = data.response
                            .split(/\r?\n/)
                            .filter(line => line.trim().startsWith("-"))
                            .map(line => line.replace(/^-\s*/, "").trim());
                    } else if (Array.isArray(data.response)) {
                        questions = data.response.map(q => q.trim()).filter(Boolean);
                    }

                    //console.log("처리된 관련 질문:", questions);
                    return questions;
                } catch (err) {
                    console.error("관련 질문 요청 에러 발생:", err);
                    return [];
                }
            };
            
            // UI 업데이트 헬퍼 함수
            const updateQaList = (updateFn) => {
                setQaList(prevQaList => {
                    const updatedList = [...prevQaList];
                    const lastIndex = updatedList.length - 1;
                    return updateFn(updatedList, lastIndex);
                });
            };

            let calculatedLocalConfidence = null;

            try {
                // 1. 로컬 답변 요청 및 즉시 표시
                console.log("1. 로컬 응답 요청 시작");
                const localStartTime = performance.now();
                let localAnswer = "응답을 받지 못했습니다.";
                try {
                    const localData = await fetchLocalResponse();
                    const localEndTime = performance.now();
                    console.log(`1. 로컬 응답 완료 (${(localEndTime - localStartTime).toFixed(2)}ms):`, localData);
                    
                    if (localData && localData.response) {
                        localAnswer = localData.response;
                        updateQaList((updatedList, lastIndex) => {
                            updatedList[lastIndex].localAnswer = localAnswer;
                            updatedList[lastIndex].answer = localAnswer;
                            return updatedList;
                        });
                        console.log("1. 로컬 답변 화면 표시 완료");
                    }
                } catch (localError) {
                    const localEndTime = performance.now();
                    console.error(`1. 로컬 응답 요청 실패 (${(localEndTime - localStartTime).toFixed(2)}ms):`, localError);
                }

                // 2. 관련 질문 요청 및 표시
                console.log("2. 관련 질문 요청 시작");
                const relatedStartTime = performance.now();
                let relatedQuestions = [];
                try {
                    relatedQuestions = await fetchRelatedQuestions();
                    const relatedEndTime = performance.now();
                    console.log(`2. 관련 질문 완료 (${(relatedEndTime - relatedStartTime).toFixed(2)}ms):`, relatedQuestions);
                    
                    if (relatedQuestions.length > 0) {
                        updateQaList((updatedList, lastIndex) => {
                            updatedList[lastIndex].relatedQuestions = relatedQuestions;
                            updatedList[lastIndex].relatedQuestionsVisible = true;
                            return updatedList;
                        });
                        console.log("2. 관련 질문 화면 표시 완료");
                    }
                } catch (questionsError) {
                    const relatedEndTime = performance.now();
                    console.error(`2. 관련 질문 요청 실패 (${(relatedEndTime - relatedStartTime).toFixed(2)}ms):`, questionsError);
                }

                // 3. 근거 문서 요청 및 표시
                console.log("3. 근거 문서 요청 시작");
                const headlinesStartTime = performance.now();
                let headlinesList = [];
                try {
                    headlinesList = await fetchHeadlinesForAnswer();
                    const headlinesEndTime = performance.now();
                    console.log(`3. 근거 문서 완료 (${(headlinesEndTime - headlinesStartTime).toFixed(2)}ms):`, headlinesList);
                    
                    if (headlinesList.length > 0) {
                        updateQaList((updatedList, lastIndex) => {
                            updatedList[lastIndex].headlines = headlinesList;
                            updatedList[lastIndex].selectedHeadline = headlinesList[0];
                            return updatedList;
                        });
                        console.log("3. 근거 문서 화면 표시 완료");
                    }
                } catch (headlinesError) {
                    const headlinesEndTime = performance.now();
                    console.error(`3. 근거 문서 목록 요청 실패 (${(headlinesEndTime - headlinesStartTime).toFixed(2)}ms):`, headlinesError);
                }

                // 4. 그래프 버튼 표시 (소스 URL 추출)
                console.log("4. 소스 URL 추출 시작");
                const sourcesStartTime = performance.now();
                let sourcesData = [];
                try {
                    // CSV에서 직접 추출하거나 답변에서 추출
                    sourcesData = await extractSourcesFromAnswer(localAnswer, currentPageId);
                    const sourcesEndTime = performance.now();
                    console.log(`소스 URL 추출 완료 (${(sourcesEndTime - sourcesStartTime).toFixed(2)}ms):`, sourcesData);
                } catch (sourcesError) {
                    const sourcesEndTime = performance.now();
                    console.error(`소스 URL 추출 실패 (${(sourcesEndTime - sourcesStartTime).toFixed(2)}ms):`, sourcesError);
                }

                // 5. 로컬 정확도 계산 및 표시
                console.log("5. 로컬 정확도 계산 시작");
                const accuracyStartTime = performance.now();
                if (localAnswer && localAnswer !== "답변을 불러오는 중..." && localAnswer !== "응답을 받지 못했습니다.") {
                    try {
                        const accuracy = await calculateAccuracy(questionText, localAnswer, 'local');
                        calculatedLocalConfidence = accuracy;
                        const accuracyEndTime = performance.now();
                        console.log(`5. 로컬 정확도 계산 완료 (${(accuracyEndTime - accuracyStartTime).toFixed(2)}ms):`, accuracy);
                        
                        updateQaList((updatedList, lastIndex) => {
                            updatedList[lastIndex].localConfidence = accuracy;
                            updatedList[lastIndex].confidence = accuracy;
                            return updatedList;
                        });
                        console.log("5. 로컬 정확도 화면 표시 완료");
                    } catch (accuracyError) {
                        const accuracyEndTime = performance.now();
                        console.error(`5. 로컬 정확도 계산 실패 (${(accuracyEndTime - accuracyStartTime).toFixed(2)}ms):`, accuracyError);
                    }
                } else {
                    console.log("5. 로컬 정확도 계산 건너뜀 (유효하지 않은 답변)");
                }

                // 6. 글로벌 답변 요청 및 표시 (정확도 제외)
                console.log("6. 글로벌 답변 요청 시작");
                const globalStartTime = performance.now();
                let globalAnswer = "응답을 받지 못했습니다.";
                try {
                    const globalData = await fetchGlobalResponse();
                    const globalEndTime = performance.now();
                    console.log(`6. 글로벌 응답 완료 (${(globalEndTime - globalStartTime).toFixed(2)}ms):`, globalData);
                    
                    if (globalData && globalData.response) {
                        globalAnswer = globalData.response;
                        updateQaList((updatedList, lastIndex) => {
                            updatedList[lastIndex].globalAnswer = globalAnswer;
                            updatedList[lastIndex].globalConfidence = calculatedLocalConfidence;
                            return updatedList;
                        });
                        console.log("6. 글로벌 답변 화면 표시 완료");
                    }
                } catch (globalError) {
                    const globalEndTime = performance.now();
                    console.error(`6. 글로벌 응답 요청 실패 (${(globalEndTime - globalStartTime).toFixed(2)}ms):`, globalError);
                }

                setServerResponseReceived(true);
                
                // 대화 히스토리에 저장
                saveToQAHistory(questionText, localAnswer, globalAnswer, "", "", headlinesList, sourcesData, relatedQuestions, calculatedLocalConfidence);
                
            } catch (error) {
                console.error("네트워크 오류:", error);
                const errorMessage = "네트워크 오류가 발생했습니다. 다시 시도해주세요.";
                updateLastAnswer(errorMessage, errorMessage, "", "", [], []);
                setServerResponseReceived(false);
            } finally {
                setIsLoading(false);
            }
        } catch (error) {
            console.error("질문 전송 중 오류 발생:", error);
            setIsLoading(false);
            
            // 오류 메시지로 답변 업데이트
            setQaList((prevQaList) => {
                const updatedList = [...prevQaList];
                const lastEntry = updatedList[updatedList.length - 1];
                lastEntry.answer = "죄송합니다. 오류가 발생했습니다.";
                return updatedList;
            });
        }
    };

    // QA 히스토리에 저장하는 함수
    const saveToQAHistory = (question, localAnswer, globalAnswer, entities, relationships, headlines, sources, relatedQuestions = [], localConfidence = null) => {
        const params = new URLSearchParams(location.search);
        const qaId = params.get("qaId");
        
        // 현재 날짜/시간
        const timestamp = new Date().toISOString();
        //마지막 항목의 정확도 가져오기
        const currentQaList = qaList;
        const lastQa = currentQaList[currentQaList.length - 1];
        // 새 대화 항목
        const newConversation = {
            question,
            answer: localAnswer, // 기본 답변은 로컬 답변으로 설정
            localAnswer,
            globalAnswer,
            timestamp,
            entities,
            relationships,
            actionButtonVisible: true,
            relatedQuestionsVisible: relatedQuestions.length > 0,
            // 정확도 정보 완전히 저장 (글로벌 정확도 제외)
            confidence: localConfidence || 0.0,
            localConfidence: localConfidence || 0.0,    //lastQa?.localConfidence || 0.0,
            globalConfidence: localConfidence || 0.0,
            // 관련 질문 저장
            relatedQuestions: relatedQuestions || [],
            headlines: headlines || [], // 근거 문서 목록 추가
            sources: sources || [], // 소스 URL 정보 추가
            satisfaction: 3, // 만족도 기본값 추가
        };
        
        if (qaId) {
            // 기존 대화에 추가
            const existingQA = qaHistory.find(qa => qa.id === qaId);
            if (existingQA) {
                const updatedConversations = [...(existingQA.conversations || []), newConversation];
                // localStorage와 Firebase 모두에 저장
                addQA({
                    ...existingQA,
                    conversations: updatedConversations,
                    timestamp: timestamp // 타임스탬프 업데이트
                }, true); // Firebase에도 저장
            }
        } else {
            // 새로운 대화 생성
            const newQAId = `qa-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            // localStorage와 Firebase 모두에 저장
            addQA({
                id: newQAId,
                pageId: currentPageId,
                question: question,
                timestamp: timestamp,
                conversations: [newConversation]
            }, true); // Firebase에도 저장
            
            // 현재 QA ID 업데이트
            setCurrentQaId(newQAId);
            // URL 업데이트 (새 qaId)
            navigate(`/chat?qaId=${newQAId}`, { replace: true });
        }
    };

    // 최신 질문의 답변 업데이트
    const updateLastAnswer = (localAnswer, globalAnswer, newEntities, newRelationships, headlines, sources, relatedQuestions = [], localConfidence = null) => {
        setQaList((prevQaList) => {
            if (prevQaList.length === 0) return prevQaList;

            const newList = [...prevQaList];
            const lastIndex = newList.length - 1;
            const confidenceValue = localConfidence !== null ? localConfidence : newList[lastIndex].localConfidence;

            const existingLocalConfidence = newList[lastIndex].localConfidence;

            newList[lastIndex] = {
                ...newList[lastIndex],
                answer: localAnswer || "답변을 불러오는 중...", // 기본 답변은 로컬 답변으로 설정
                localAnswer: localAnswer || "로컬 답변을 불러오는 중...",
                globalAnswer: globalAnswer || "글로벌 답변을 불러오는 중...",
                confidence: confidenceValue,
                localConfidence: confidenceValue,
                globalConfidence: confidenceValue, // 글로벌 정확도는 계산하지 않음
                entities: newEntities,
                relationships: newRelationships,
                headlines: headlines || [], // 근거 문서 목록 추가
                selectedHeadline: headlines && headlines.length > 0 ? headlines[0] : '', // 기본 선택 근거 문서
                sources: sources || [], // 소스 URL 정보 추가
                relatedQuestions: relatedQuestions || [], // 관련 질문 추가
            };
            return newList;
        });
    };

    const handleShowGraph = async () => {
        if (isLoading) {
            console.log("이미 그래프를 로딩 중입니다.");
            return;
        }

        if (!serverResponseReceived) {
            console.log("서버 응답을 기다리는 중입니다.");
            showAlert("알림", "서버 응답을 기다리는 중입니다. 잠시 후 다시 시도해주세요.");
            return;
        }

        if (!currentPageId) {
            console.error("페이지 ID가 없습니다.");
            showAlert("오류", "페이지 ID가 설정되지 않았습니다. 페이지를 새로고침하거나 다시 시도해주세요.");
            return;
        }

        try {
            setIsLoading(true);
            console.log("그래프 데이터 로딩 시작 (최신 질의응답 기준)");

            // 캐시 사용하지 않고 항상 최신 데이터 로드
            const jsonData = answerGraphData;

            console.log("그래프 데이터 로드 성공:", jsonData);

            if (!jsonData || !jsonData.nodes || !jsonData.edges) {
                throw new Error("유효하지 않은 그래프 데이터입니다.");
            }

            setGraphData(jsonData);
            setShowGraph(true);

        } catch (error) {
            console.error("그래프 데이터 로드 실패:", error);
            showAlert("오류", `그래프 데이터를 불러오는 데 실패했습니다: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    // 그래프 닫기 함수
    const handleCloseGraph = () => {
        setShowGraph(false);
    };
    
    
    // 선택된 파일 취소
    const handleCancelFile = () => {
        setSelectedFile(null);
    };
    
    // URL 제거
    const handleRemoveUrl = (index) => {
        const newUrls = [...addedUrls];
        newUrls.splice(index, 1);
        setAddedUrls(newUrls);
    };

    // 질문을 입력 후 전송
    const handleSendQuestion = () => {
        if (newQuestion.trim() && !isLoading) {
            console.log("질문 전송 시작:", {
            question: newQuestion.trim(),
            hasFile: !!selectedFile,
            fileInfo: selectedFile ? {
                name: selectedFile.name,
                size: selectedFile.size,
                type: selectedFile.type
            } : null,
            hasUrls: addedUrls.length > 0,
            urls: addedUrls
        });
            sendQuestion(newQuestion.trim());
        }
        
    };
      // 파일 선택 처리 함수
    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            console.log("파일 선택됨:", file);
            setSelectedFile(file);

            // 같은 파일 다시 선택해도 onChange 이벤트가 발생하도록 초기화
            event.target.value = "";
        }
    };

    // 문서 버튼 클릭 시 파일 선택창 열기
    const handleDocumentOptionClick = () => {
        setSearchType('document');
        fileInputRef.current.click();
        setIsDropdownVisible(false);
    };

    // URL 선택 시 처리
    const handleUrlOptionClick = () => {
        setSearchType('url');
        setShowUrlInput(true); // 입력창 보이게
    };

    const handleAddUrl = () => {
        const urlPattern = /^(https?:\/\/)?([\w-]+\.)+[\w-]{2,}(\/\S*)?$/;
        if (!urlPattern.test(urlInput.trim())) {
            showAlert("입력 오류", "유효한 URL을 입력해주세요.");
            setUrlInput('');
            return;
        }

        setAddedUrls([...addedUrls, urlInput.trim()]);
        setUrlInput('');
        setShowUrlInput(false); // 입력창 닫기
    };
    
    // 사이드바 토글
    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen);
    };
    
    // 근거 문서 목록 가져오기 또는 로컬 저장소에서 불러오기
    // headline 가져올 때도 localStorage만 사용
    const fetchHeadlinesForMessage = async (index) => {
        const currentQA = qaList[index];
        
        // 이미 해당 메시지에 headline 정보가 있는지 확인
        if (currentQA && currentQA.headlines && currentQA.headlines.length > 0) {
            return currentQA.headlines;
        }
        
        // localStorage에서 현재 QA와 대화 인덱스로 headline 정보를 찾음
        if (currentQaId) {
            const qaItem = qaHistory.find(qa => qa.id === currentQaId);
            if (qaItem && qaItem.conversations && qaItem.conversations[index] && 
                qaItem.conversations[index].headlines && 
                qaItem.conversations[index].headlines.length > 0) {
                return qaItem.conversations[index].headlines;
            }
        }
        
        // 서버에서 headline 정보 가져오기
        setHeadlinesLoading(true);
        try {
            const response = await fetch(`${BASE_URL}/api/context-sources?page_id=${currentPageId}`);
            if (!response.ok) {
                throw new Error(`서버 응답 오류: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            if (!data.headlines || data.headlines.length === 0) {
                throw new Error("사용 가능한 headline이 없습니다");
            }
            
            if (currentQaId) { 
                // 가져온 headline 정보 QA 히스토리에 저장 (localStorage와 Firebase 모두)
                updateQAHeadlines(currentQaId, index, data.headlines, true); // Firebase에도 저장
            }
            
            setQaList(prevQaList => { // 현재 대화 목록에도 headline 정보 추가
                const updatedList = [...prevQaList];
                if (updatedList[index]) {
                    updatedList[index].headlines = data.headlines;
                    updatedList[index].selectedHeadline = data.headlines[0];
                }
                return updatedList;
            });
            
            return data.headlines;
            
        } catch (error) {
            console.error("headline 목록 가져오기 실패:", error);
            return [];
        } finally {
            setHeadlinesLoading(false);
        }
    };

    // HWP 파일 확인 함수
    const checkIfHwpFile = async (headline) => {
        if (!headline) return false;
        
        try {
            const processedHeadline = headline.trim();
            const encodedHeadline = encodeURIComponent(processedHeadline);
            const url = `${BASE_URL}/api/document/${encodedHeadline}?page_id=${currentPageId}`;
            
            const response = await fetch(url, { method: 'HEAD' });
            
            // 서버에서 HWP 파일에 대한 에러 응답 확인
            if (!response.ok && response.status === 400) {
                const errorData = await fetch(url).then(res => res.json()).catch(() => ({}));
                if (errorData.error && errorData.error.includes('HWP')) {
                    return true;
                }
            }
            
            return false;
        } catch (error) {
            console.error('HWP 파일 확인 오류:', error);
            return false;
        }
    };

    // HWP 파일 다운로드 알림 및 다운로드 처리
    const handleHwpDownload = (headline) => {
        const processedHeadline = headline.trim();
        const encodedHeadline = encodeURIComponent(processedHeadline);
        const downloadUrl = `${BASE_URL}/api/download/${encodedHeadline}?page_id=${currentPageId}`;
        
        showConfirm(
            "문서 다운로드", 
            `"${headline}" 파일은 HWP 형식입니다.\n현재 뷰어에서는 지원되지 않으니 파일을 다운로드 후 확인해 주세요.`,
            () => {
                const link = document.createElement('a');
                link.href = downloadUrl;
                link.download = '';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                setTimeout(() => {
                    showAlert("다운로드 완료", "파일 다운로드가 완료되었습니다.\n다운로드된 HWP 파일을 한글 프로그램으로 열어서 확인해주세요.");
                }, 500);
            }
        );
    };

    // Document URL 업데이트
    const updateDocumentUrl = async (headline) => {
    if (!headline) return false;
        
    // HWP 파일인지 먼저 확인
    const isHwpFile = await checkIfHwpFile(headline);
        if (isHwpFile) {
            handleHwpDownload(headline);
            return false; // HWP 파일이므로 문서 뷰어를 열지 않음
        }

        // 특수문자 처리 및 파일명 정리 (괄호 등에 대한 처리)
        let processedHeadline = headline.trim();
        const encodedHeadline = encodeURIComponent(processedHeadline); // 한글 인코딩 처리
        
        // 파일명에 사용될 수 있는 확장자 체크를 서버에서 처리하도록 함
        const url = `${BASE_URL}/api/document/${encodedHeadline}?page_id=${currentPageId}`;
        
        console.log(`문서 요청 URL: ${url}`);
        setPdfUrl(url);
        
        // 파일 로딩 확인을 위한 테스트 요청
        try {
            const response = await fetch(url, { method: 'HEAD' });
            console.log(`문서 응답 상태: ${response.status}`);
            if (!response.ok) {
                console.error('문서를 찾을 수 없습니다. 확인 필요.');
                return false;
            }
            return true;
        } catch (error) {
            console.error('문서 요청 오류:', error);
            return false;
        }
    };

    // 근거 문서 열기 핸들러
    const handleShowDocument = async (index, specificHeadline = null) => {
        setCurrentMessageIndex(index);
        
        if (showDocument && currentMessageIndex === index && !specificHeadline) {
            setShowDocument(false);
            setCurrentMessageIndex(null);
            document.querySelector('.chat-container').classList.remove('shift-left');
            return;
        }
        
        setShowGraph(false); // 그래프 닫기
        setDocumentErrorMessage('');
        
        setQaList(prevQaList => { // 해당 메시지의 문서 로드 중 상태 설정
            const updatedList = [...prevQaList];
            if (updatedList[index]) {
                updatedList[index].isDocumentLoading = true;
            }
            return updatedList;
        });
        
        // 해당 메시지 headline 목록 가져오기
        const messageHeadlines = await fetchHeadlinesForMessage(index);
        
        if (messageHeadlines.length > 0) {
            setHeadlines(messageHeadlines);
            
            // 특정 헤드라인이 지정되었으면 해당 헤드라인 선택
            let selectedHead = specificHeadline || '';
            
            // 특정 헤드라인이 지정되지 않은 경우 기존 로직 사용
            if (!selectedHead) {
                // 로컬 대화 목록에서 선택된 headline 확인
                if (qaList[index] && qaList[index].selectedHeadline) {
                    selectedHead = qaList[index].selectedHeadline;
                }
                // QA 히스토리에서 선택된 headline 확인
                else if (currentQaId) {
                    const qaItem = qaHistory.find(qa => qa.id === currentQaId);
                    if (qaItem && qaItem.conversations && qaItem.conversations[index] && 
                        qaItem.conversations[index].selectedHeadline) {
                        selectedHead = qaItem.conversations[index].selectedHeadline;
                    }
                }
                // 선택된 headline 없으면 첫 번째 선택
                if (!selectedHead || !messageHeadlines.includes(selectedHead)) {
                    selectedHead = messageHeadlines[0];
                }
            }
            
            setSelectedHeadline(selectedHead);
            
            // HWP 파일 확인 후 뷰어 열기 여부 결정
            const shouldOpenViewer = await updateDocumentUrl(selectedHead);
            
            if (shouldOpenViewer) {
                // HWP 파일이 아닌 경우에만 뷰어 열기
                setShowDocument(true);
                document.querySelector('.chat-container').classList.add('shift-left');
            } else {
                // HWP 파일인 경우 뷰어를 열지 않고 현재 상태 유지
                // 이미 updateDocumentUrl에서 다운로드 처리가 완료됨
                console.log('HWP 파일이므로 뷰어를 열지 않습니다.');
            }
        } else {
            setDocumentErrorMessage("근거 문서를 찾을 수 없습니다.");
        }
        
        setQaList(prevQaList => { // 문서 로드 완료 상태
            const updatedList = [...prevQaList];
            if (updatedList[index]) {
                updatedList[index].isDocumentLoading = false;
            }
            return updatedList;
        });
    };

    // headline 업데이트 시 localStorage, firebase 사용
    const handleHeadlineSelect = (headline) => {
        setSelectedHeadline(headline);
        updateDocumentUrl(headline); // PDF URL 대신 document URL로 업데이트
        
        // 현재 선택된 headline 저장 (localStorage와 Firebase 모두)
        if (currentQaId && currentMessageIndex !== null) {
            // QA 히스토리에 선택된 headline 업데이트 (Firebase에도 저장)
            updateSelectedHeadline(currentQaId, currentMessageIndex, headline, true); // Firebase에도 저장
            // 현재 대화 목록에 선택된 headline 업데이트
            setQaList(prevQaList => {
                const updatedList = [...prevQaList];
                if (updatedList[currentMessageIndex]) {
                    updatedList[currentMessageIndex].selectedHeadline = headline;
                }
                return updatedList;
            });
        }
    };
    
    const handleDownloadDocument = async (headline) => {
        if (!headline) return;
        
        try {
            // 특수문자 처리 및 파일명 정리
            let processedHeadline = headline.trim();
            const encodedHeadline = encodeURIComponent(processedHeadline);
            
            // 다운로드 URL 생성 (기존 document API와 다른 download API 사용)
            const downloadUrl = `${BASE_URL}/api/download/${encodedHeadline}?page_id=${currentPageId}`;
            
            console.log(`문서 다운로드 URL: ${downloadUrl}`);
            
            // fetch를 사용하여 서버 응답 확인 후 다운로드
            const response = await fetch(downloadUrl);
            
            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }
            
            // Content-Disposition 헤더에서 실제 파일명 추출
            const contentDisposition = response.headers.get('Content-Disposition');
            let actualFilename = headline; // 기본값
            
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    actualFilename = filenameMatch[1].replace(/['"]/g, '');
                    // UTF-8 인코딩된 파일명 처리
                    if (actualFilename.startsWith('UTF-8\'\'')) {
                        actualFilename = decodeURIComponent(actualFilename.substring(7));
                    }
                }
            }
            
            // Blob으로 파일 데이터 처리
            const blob = await response.blob();
            
            // 다운로드 링크 생성
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = actualFilename; // 서버에서 제공한 실제 파일명 사용
            link.target = '_blank';
            
            // 다운로드 실행
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // 메모리 정리
            window.URL.revokeObjectURL(url);
            
            console.log('원본 문서 다운로드 완료:', actualFilename);
            
        } catch (error) {
            console.error('문서 다운로드 중 오류:', error);
            showAlert("다운로드 오류", `문서 다운로드에 실패했습니다: ${error.message}`);
        }
    };

    //정확도 계산
    const calculateAccuracy = async (question, answer, answerType = 'local') => {
        try {
            const pageId = localStorage.getItem("currentPageId") || currentPageId;
            if (!pageId) {
                console.log("페이지 ID 또는 질문 텍스트가 없음");
                return [];
            }
            console.log(`${answerType} 정확도 계산 요청:`, { question, answer });
            
            const response = await fetch(`${BASE_URL}/calculate-accuracy`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    question: question,
                    answer: answer,
                    answer_type: answerType,
                    page_id: pageId,
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log(`${answerType} 정확도 계산 완료:`, result);
            
            // 백분율로 반환 (소수점 1자리)
            return parseFloat(result.percentage) || 0.0;
            
        } catch (error) {
            console.error(`${answerType} 정확도 계산 실패:`, error);
            return 0.0; // 기본값
        }
    };

    return (
        <div className={`chat-page-container ${showGraph ? "with-graph" : ""}`}>
            <Sidebar 
                isSidebarOpen={isSidebarOpen} 
                toggleSidebar={toggleSidebar} 
            />
            {/* 모달 컴포넌트 추가 */}
            <Modal
                isOpen={modalState.isOpen}
                onClose={closeModal}
                title={modalState.title}
                message={modalState.message}
                type={modalState.type}
                onConfirm={handleModalConfirm}
            />
            
            <div className={`chat-container ${showGraph || showDocument ? "shift-left" : ""} ${isSidebarOpen ? "sidebar-open" : ""}`}>
                <div className="domain-name">
                    <h2>{systemName + " Q&A 시스템" || "한성대 Q&A 시스템"}</h2>
                </div>
                <div className="chat-messages">
                    {qaList.map((qa, index) => (
                        <ChatMessage
                            key={index}
                            qa={qa}
                            index={index}
                            qaId={currentQaId}
                            // conversationIndex={qaIndex}
                            handleShowGraph={handleShowGraph}
                            showGraph={showGraph}
                            handleShowDocument={handleShowDocument}
                            showDocument={showDocument && currentMessageIndex === index}
                            handleDownloadDocument={handleDownloadDocument}
                            sendQuestion={sendQuestion}
                        />
                    ))}
                    <div ref={chatEndRef} />
                </div>

                <ChatInput
                    newQuestion={newQuestion}
                    setNewQuestion={setNewQuestion}
                    handleSendQuestion={handleSendQuestion}
                    handleUrlOptionClick={handleUrlOptionClick}
                    handleDocumentOptionClick={handleDocumentOptionClick}
                    addedUrls={addedUrls}
                    setAddedUrls={setAddedUrls}
                    selectedFile={selectedFile}
                    setSelectedFile={setSelectedFile}
                    showUrlInput={showUrlInput}
                    setShowUrlInput={setShowUrlInput}
                    urlInput={urlInput}
                    setUrlInput={setUrlInput}
                    handleAddUrl={handleAddUrl}
                />
                {/* 숨겨진 파일 입력 필드 */}
                    <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                    accept=".pdf,.doc,.docx,.txt"
                />
                {showGraph && graphData && (
                    <div className="graph-container">
                        <button className="close-graph" onClick={handleCloseGraph}>닫기</button>
                        <NetworkChart data={graphData} />
                    </div>
                )}
                
                {showDocument && (
                    <div className="document-viewer">
                        <div className="document-viewer-header">
                            <div className="document-title">
                                <h3>근거 문서</h3>
                            </div>
                            <div className="document-controls">
                                <select 
                                    value={selectedHeadline} 
                                    onChange={(e) => handleHeadlineSelect(e.target.value)}
                                    className="headline-selector"
                                    disabled={headlinesLoading || headlines.length === 0}
                                >
                                    {headlines.map((headline, idx) => (
                                        <option key={idx} value={headline}>{headline}</option>
                                    ))}
                                </select>
                                <button 
                                    className="download-button"
                                    onClick={() => handleDownloadDocument(selectedHeadline)}
                                    title="원본 문서 다운로드"
                                    disabled={!selectedHeadline}
                                >
                                    <img 
                                        src="/assets/download2.png" 
                                        alt="다운로드" 
                                    />
                                </button>
                                <button 
                                    className="close-button"
                                    onClick={() => {
                                        setShowDocument(false);
                                        document.querySelector('.chat-container').classList.remove('shift-left');
                                    }}
                                    title="닫기"
                                >
                                x
                                </button>
                            </div>
                        </div>
                        <div className="pdf-viewer-container">
                            {documentErrorMessage ? (
                                <div className="error-message">{documentErrorMessage}</div>
                            ) : pdfUrl ? (
                                <iframe 
                                    src={pdfUrl} 
                                    className="pdf-viewer-iframe"
                                    title="PDF 뷰어"
                                ></iframe>
                            ) : (
                                <div className="loading-indicator">PDF 로딩 중...</div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default ChatPage;