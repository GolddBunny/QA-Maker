import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/ChatPage.css";
import NetworkChart from "../components/charts/NetworkChart";
import ChatMessage from "../components/chat/ChatMessage";
import ChatInput from "../components/chat/ChatInput";
import { usePageContext } from "../utils/PageContext";
import { useQAHistoryContext } from "../utils/QAHistoryContext";
import Sidebar from "../components/navigation/Sidebar";

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

    const scrollToBottom = () => { //새 질문 시 아래로 스크롤
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
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

    // 답변에서 소스 URL 추출 함수 추가
    const extractSourcesFromAnswer = async (answerText, pageId) => {
        try {
            //console.log("소스 추출 시작:", answerText);
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
            // console.log("서버에서 받은 소스 데이터:", data.sources);
            
            // 소스 데이터 검증
            if (!Array.isArray(data.sources)) {
                console.error("소스 데이터가 배열이 아닙니다:", data.sources);
                return [];
            }
            
            return data.sources;
        } catch (error) {
            console.error("소스 URL 추출 실패:", error);
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

    // 그래프 로드 함수
    const handleShowGraph = async () => {
        // 이미 로딩 중이면 중복 실행 방지
        if (isLoading) {
            console.log("이미 그래프를 로딩 중입니다.");
            return;
        }

        // 서버 응답 확인
        if (!serverResponseReceived) {
            console.log("서버 응답을 기다리는 중입니다.");
            alert("서버 응답을 기다리는 중입니다. 잠시 후 다시 시도해주세요.");
            return;
        }

        // 필수 데이터 확인
        if (!currentPageId) {
            console.error("페이지 ID가 없습니다.");
            alert("페이지 ID가 설정되지 않았습니다. 페이지를 새로고침하거나 다시 시도해주세요.");
            return;
        }

        try {
            // 로딩 상태 설정
            setIsLoading(true);
            console.log("그래프 데이터 로딩 시작");

            // 캐시 키 설정
            const cacheKey = `${entities}-${relationships}`;
            
            // 메모리 캐시 확인
            if (graphDataCacheRef.current[cacheKey]) {
                console.log("메모리 캐시에서 그래프 데이터 로드");
                setGraphData(graphDataCacheRef.current[cacheKey]);
                setShowGraph(true);
                setIsLoading(false);
                return;
            }
            
            // // API 호출
            // const generateResponse = await fetch("http://localhost:5000/generate-graph", {
            //     method: "POST",
            //     headers: { 
            //         "Content-Type": "application/json"
            //     },
            //     body: JSON.stringify({
            //         page_id: currentPageId,
            //     })
            // });

            // // API 응답 처리
            // const generateData = await generateResponse.json();

            // if (!generateResponse.ok) {
            //     throw new Error(`그래프 생성 실패: ${generateData.error || "알 수 없는 오류"}`);
            // }
            
            // console.log("그래프 생성 API 응답:", generateData);
            
            // 캐시를 방지하기 위한 타임스탬프 추가
            const timestamp = new Date().getTime();
            
            // JSON 파일 로드
            const jsonResponse = await fetch(`./json/answer_graphml_data.json?t=${timestamp}`, {
                method: "GET",  // 명시적으로 GET 메서드 지정
                headers: {
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                },
                cache: "no-store"  // fetch API의 캐시 옵션
            });

            if (!jsonResponse.ok) {
            const errorText = await jsonResponse.text().catch(() => "응답 텍스트를 읽을 수 없음");
            console.error("JSON 응답 오류:", jsonResponse.status, errorText);
            throw new Error(`JSON 파일 로드 실패 (상태: ${jsonResponse.status}): ${errorText}`);
        }
        
            let jsonData;
            try {
                jsonData = await jsonResponse.json();
            } catch (jsonError) {
                console.error("JSON 파싱 오류:", jsonError);
                throw new Error("JSON 데이터를 파싱할 수 없습니다.");
            }
            
            console.log("그래프 데이터 로드 성공:", jsonData);
            // 그래프 데이터 유효성 검사
            if (!jsonData || !jsonData.nodes || !jsonData.edges) {
                throw new Error("유효하지 않은 그래프 데이터입니다.");
            }

            // 데이터 저장 및 그래프 표시
            graphDataCacheRef.current[cacheKey] = jsonData;
            setGraphData(jsonData);
            setShowGraph(true);
            
        } catch (error) {
            console.error("그래프 데이터 로드 실패:", error);
            alert(`그래프 데이터를 불러오는 데 실패했습니다: ${error.message}`);
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
            alert('유효한 URL을 입력해주세요.');
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

    // PDF URL 업데이트
    const updatePdfUrl = (headline) => {
        if (!headline) return;
        
        const encodedHeadline = encodeURIComponent(headline); // 한글 인코딩 처리
        const url = `http://localhost:5000/api/pdf/${encodedHeadline}?page_id=${currentPageId}`;
        setPdfUrl(url);
    };

    // 근거 문서 열기 핸들러
    const handleShowDocument = async (index) => {
        setCurrentMessageIndex(index);
        
        if (showDocument && currentMessageIndex === index) {
            setShowDocument(false);
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
            // 이미 선택된 headline이 있는지 확인
            let selectedHead = '';
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
            
            setSelectedHeadline(selectedHead);
            updatePdfUrl(selectedHead);
            setShowDocument(true);
            document.querySelector('.chat-container').classList.add('shift-left');
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
        updatePdfUrl(headline);
        
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
    
    return (
        <div className={`chat-page-container ${showGraph ? "with-graph" : ""}`}>
            <Sidebar 
                isSidebarOpen={isSidebarOpen} 
                toggleSidebar={toggleSidebar} 
            />
            
            <div className={`chat-container ${showGraph || showDocument ? "shift-left" : ""} ${isSidebarOpen ? "sidebar-open" : ""}`}>
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
                            
                        />
                    ))}
                    <div ref={chatEndRef} />
                </div>

                <ChatInput 
                    newQuestion={newQuestion} 
                    setNewQuestion={setNewQuestion} 
                    handleSendQuestion={handleSendQuestion} 
                    isLoading={isLoading} 
                    handleUrlOptionClick={handleUrlOptionClick}
                    handleDocumentOptionClick={handleDocumentOptionClick}
                />
                {/* 숨겨진 파일 입력 필드 */}
                <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                style={{ display: 'none' }}
                accept=".pdf,.doc,.docx,.txt"
                />
                {showUrlInput && (
                    <div className="url-input-box-chat">
                        <input
                        type="text"
                        placeholder="URL을 입력하세요"
                        value={urlInput}
                        onChange={(e) => setUrlInput(e.target.value)}
                        className="url-input-main"
                        />
                        <button 
                        onClick={() => {
                            handleAddUrl();
                            setShowUrlInput(false); // 입력 후 닫기
                        }} 
                        className="add-url-btn"
                        >
                        추가
                        </button>
                    </div>
                    )}

                    {selectedFile && (
                        <div className="selected-file-container">
                        <div className="selected-file">
                        <img src="/assets/document.png" alt="파일" className="file-icon" />
                        <span className="file-name">{selectedFile.name}</span>
                        <button 
                            className="file-cancel" 
                            onClick={() => setSelectedFile(null)}
                            title="파일 선택 취소"
                        >
                            ×
                        </button>
                        </div>
                    </div>
                    )}

                    {addedUrls.length > 0 && (
                        <div className="url-list">
                        {addedUrls.map((url, index) => (
                            <div key={index} className="selected-file-container">
                            <div className="selected-file">
                                <span className='url-icon'>🌐</span>
                                <span>{url}</span>
                                <button 
                                className="file-cancel"
                                onClick={() => {
                                    const newUrls = [...addedUrls];
                                    newUrls.splice(index, 1);
                                    setAddedUrls(newUrls);
                                }}
                                title="URL 제거"
                                >
                                ×
                                </button>
                            </div>
                            </div>
                        ))}
                        </div>
                    )}

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