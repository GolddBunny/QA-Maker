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
            // 해당 대화의 모든 질문-답변 로드
            setQaList(qaItem.conversations || []);
            
            // 엔티티와 관계 정보 설정 (마지막 대화의 정보 사용)
            if (qaItem.conversations && qaItem.conversations.length > 0) {
                const lastConversation = qaItem.conversations[qaItem.conversations.length - 1];
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
            
            // Sources 형식 확인
            if (!answerText.includes("Sources")) {
                console.log("Sources 표기가 없어 소스 추출을 건너뜁니다.");
                return [];
            }
            
            const response = await fetch("http://localhost:5000/extract-sources", {
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
            
            // 응답 형식 검증 및 로깅
            console.log("서버에서 받은 소스 데이터:", data.sources);
            
            // 소스 데이터 검증
            if (!Array.isArray(data.sources)) {
                console.error("소스 데이터가 배열이 아닙니다:", data.sources);
                return [];
            }
            
            // 각 소스 데이터의 구조 검증 및 로깅
            const validSources = data.sources.filter(source => {
                if (!source || typeof source !== 'object') {
                    console.warn("유효하지 않은 소스 데이터:", source);
                    return false;
                }
                
                // source_id는 필수, url과 title 중 하나는 있어야 함
                if (!source.source_id || (!source.url && !source.title)) {
                    console.warn("소스 ID가 없거나 URL/Title이 모두 없는 소스:", source);
                    return false;
                }
                
                console.log(`소스 ${source.source_id}: Title="${source.title || '없음'}", URL="${source.url || '없음'}"`);
                return true;
            });
            
            console.log(`총 ${data.sources.length}개 소스 중 ${validSources.length}개 유효한 소스 추출됨`);
            
            return validSources;
            
        } catch (error) {
            console.error("소스 URL/Title 추출 실패:", error);
            return [];
        }
    };

    // 질문 전송 함수 (병렬 요청 방식)
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
        
        // 각 방식별 서버 요청 함수
        const fetchLocalResponse = async () => {
            const response = await fetch("http://localhost:5000/run-local-query", {
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
            return fetch("http://localhost:5000/run-global-query", {
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
                const response = await fetch(`http://localhost:5000/api/context-sources?page_id=${currentPageId}`);
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
                const response = await fetch("http://localhost:5000/generate-related-questions", {
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

                console.log("처리된 관련 질문:", questions);
                return questions;
            } catch (err) {
                console.error("관련 질문 요청 에러 발생:", err);
                return [];
            }
        };
        
        // 부분 응답 업데이트를 위한 새 함수 추가
        const updatePartialAnswer = (type, answer) => {
            setQaList(prevQaList => {
                const updatedList = [...prevQaList];
                const lastIndex = updatedList.length - 1;
                
                if (type === 'local') {
                    updatedList[lastIndex].localAnswer = answer;
                } else if (type === 'global') {
                    updatedList[lastIndex].globalAnswer = answer;
                }
                
                // 기본 답변 업데이트
                updatedList[lastIndex].answer = answer;
                
                return updatedList;
            });
        };

        try {
            // 로컬 응답과 글로벌 응답을 먼저 가져오기
            console.log("로컬 및 글로벌 응답 요청 시작");
            let localData, globalData;
            
            try {
                localData = await fetchLocalResponse();
                console.log("로컬 응답 받음:", localData);
                
                // 로컬 응답이 성공적으로 도착하면 즉시 UI 업데이트
                if (localData && localData.response) {
                    const localAnswer = localData.response;
                    updatePartialAnswer('local', localAnswer);
                }
            } catch (localError) {
                console.error("로컬 응답 요청 실패:", localError);
                localData = { response: "로컬 응답을 받지 못했습니다." };
            }
            
            try {
                globalData = await fetchGlobalResponse();
                console.log("글로벌 응답 받음:", globalData);
                
                // 글로벌 응답이 성공적으로 도착하면 즉시 UI 업데이트
                if (globalData && globalData.response) {
                    const globalAnswer = globalData.response;
                    updatePartialAnswer('global', globalAnswer);
                }
            } catch (globalError) {
                console.error("글로벌 응답 요청 실패:", globalError);
                globalData = { response: "글로벌 응답을 받지 못했습니다." };
            }
            
            // 최종 응답 정보 추출
            const localAnswer = localData?.response || "응답을 받지 못했습니다.";
            const globalAnswer = globalData?.response || "응답을 받지 못했습니다.";
            
            // 나머지 데이터 가져오기
            let headlinesList = [];
            let relatedQuestions = [];
            
            try {
                headlinesList = await fetchHeadlinesForAnswer();
                console.log("근거 문서 목록 받음:", headlinesList);
            } catch (headlinesError) {
                console.error("근거 문서 목록 요청 실패:", headlinesError);
            }
            
            try {
                relatedQuestions = await fetchRelatedQuestions();
                console.log("관련 질문 받음:", relatedQuestions);
            } catch (questionsError) {
                console.error("관련 질문 요청 실패:", questionsError);
            }
            
            // 소스 URL 추출 (로컬 답변에서)
            const sourcesData = await extractSourcesFromAnswer(localAnswer, currentPageId);
            console.log("추출된 소스 URL:", sourcesData);
            
            // 최종 업데이트
            updateLastAnswer(localAnswer, globalAnswer, "", "", headlinesList, sourcesData);
            setServerResponseReceived(true);
            
            // 그래프 및 관련 질문 버튼 표시
            setQaList(prevQaList => {
                const updatedList = [...prevQaList];
                const lastIndex = updatedList.length - 1;

                updatedList[lastIndex] = {
                    ...updatedList[lastIndex],
                    actionButtonVisible: true,
                    relatedQuestionsVisible: true,
                    relatedQuestions: relatedQuestions,
                };

                return updatedList;
            });
            
            // 대화 히스토리에 저장
            saveToQAHistory(questionText, localAnswer, globalAnswer, "", "", headlinesList, sourcesData);
            
        } catch (error) {
            console.error("네트워크 오류:", error);
            const errorMessage = "네트워크 오류가 발생했습니다. 다시 시도해주세요.";
            updateLastAnswer(errorMessage, errorMessage, "", "", [], []);
            setServerResponseReceived(false);
        } finally {
            setIsLoading(false);
        }
    };

    // QA 히스토리에 저장하는 함수
    const saveToQAHistory = (question, localAnswer, globalAnswer, entities, relationships, headlines, sources) => {
        const params = new URLSearchParams(location.search);
        const qaId = params.get("qaId");
        
        // 현재 날짜/시간
        const timestamp = new Date().toISOString();
        
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
            relatedQuestionsVisible: true,
            confidence: 99,
            localConfidence: 99,
            globalConfidence: 90,
            headlines: headlines || [], // 근거 문서 목록 추가
            sources: sources || [], // 소스 URL 정보 추가
        };
        
        if (qaId) {
            // 기존 대화에 추가
            const existingQA = qaHistory.find(qa => qa.id === qaId);
            if (existingQA) {
                const updatedConversations = [...(existingQA.conversations || []), newConversation];
                addQA({
                    ...existingQA,
                    conversations: updatedConversations,
                    timestamp: timestamp // 타임스탬프 업데이트
                });
            }
        } else {
            // 새로운 대화 생성
            const newQAId = `qa-${Date.now()}`;
            addQA({
                id: newQAId,
                pageId: currentPageId,
                question: question,
                timestamp: timestamp,
                conversations: [newConversation]
            });
            // 현재 QA ID 업데이트
            setCurrentQaId(newQAId);
            // URL 업데이트 (새 qaId)
            navigate(`/chat?qaId=${newQAId}`, { replace: true });
        }
    };

    // 최신 질문의 답변 업데이트
    const updateLastAnswer = (localAnswer, globalAnswer, newEntities, newRelationships, headlines, sources) => {
        setQaList((prevQaList) => {
            if (prevQaList.length === 0) return prevQaList;

            const newList = [...prevQaList];
            const lastIndex = newList.length - 1;
            newList[lastIndex] = {
                ...newList[lastIndex],
                answer: localAnswer || "답변을 불러오는 중...", // 기본 답변은 로컬 답변으로 설정
                localAnswer: localAnswer || "로컬 답변을 불러오는 중...",
                globalAnswer: globalAnswer || "글로벌 답변을 불러오는 중...",
                confidence: 99,
                localConfidence: 99,
                globalConfidence: 90,
                entities: newEntities,
                relationships: newRelationships,
                headlines: headlines || [], // 근거 문서 목록 추가
                selectedHeadline: headlines && headlines.length > 0 ? headlines[0] : '', // 기본 선택 근거 문서
                sources: sources || [], // 소스 URL 정보 추가
                
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
            console.log("그래프 데이터 로딩 시작");

            const cacheKey = `${entities}-${relationships}`;
            
            if (graphDataCacheRef.current[cacheKey]) {
                console.log("메모리 캐시에서 그래프 데이터 로드");
                setGraphData(graphDataCacheRef.current[cacheKey]);
                setShowGraph(true);
                setIsLoading(false);
                return;
            }

            // 여기서 fetch 대신 import로 가져온 데이터를 사용
            const jsonData = answerGraphData;

            console.log("그래프 데이터 로드 성공:", jsonData);

            if (!jsonData || !jsonData.nodes || !jsonData.edges) {
                throw new Error("유효하지 않은 그래프 데이터입니다.");
            }

            graphDataCacheRef.current[cacheKey] = jsonData;
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
            sendQuestion(newQuestion.trim());
        }
        
    };
      // 파일 선택 처리 함수
    const handleFileChange = (e) => {
        if (e.target.files.length > 0) {
        const file = e.target.files[0];
        setSelectedFile(file);
        console.log('선택된 파일:', file.name);
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
    const fetchHeadlinesForMessage = async (index) => {
        const currentQA = qaList[index];
        
        // 이미 해당 메시지에 headline 정보가 있는지 확인
        if (currentQA && currentQA.headlines && currentQA.headlines.length > 0) {
            return currentQA.headlines;
        }
        
        // 로컬 저장소에서 현재 QA와 대화 인덱스로 headline 정보를 찾음
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
            const response = await fetch(`http://localhost:5000/api/context-sources?page_id=${currentPageId}`);
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
            
            if (currentQaId) { // 가져온 headline 정보 QA 히스토리에 저장
                updateQAHeadlines(currentQaId, index, data.headlines);
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
            const url = `http://localhost:5000/api/document/${encodedHeadline}?page_id=${currentPageId}`;
            
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
        const downloadUrl = `http://localhost:5000/api/download/${encodedHeadline}?page_id=${currentPageId}`;
        
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
        const url = `http://localhost:5000/api/document/${encodedHeadline}?page_id=${currentPageId}`;
        
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

    // headline 선택
    const handleHeadlineSelect = (headline) => {
        setSelectedHeadline(headline);
        updateDocumentUrl(headline); // PDF URL 대신 document URL로 업데이트
        
        // 현재 선택된 headline 저장
        if (currentQaId && currentMessageIndex !== null) {
            // QA 히스토리에 선택된 headline 업데이트
            updateSelectedHeadline(currentQaId, currentMessageIndex, headline);
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
            const downloadUrl = `http://localhost:5000/api/download/${encodedHeadline}?page_id=${currentPageId}`;
            
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
                    <h2>{systemName + " QA 시스템" || "QA시스템"}</h2>
                </div>
                <div className="chat-messages">
                    {qaList.map((qa, index) => (
                        <ChatMessage 
                            key={index} 
                            qa={qa} 
                            index={index} 
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
                                    📥
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