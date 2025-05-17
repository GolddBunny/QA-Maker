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
    const { qaHistory, addQA } = useQAHistoryContext(); // QA 히스토리 컨텍스트 사용
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

        const params = new URLSearchParams(location.search);
        const initialQuestion = params.get("question");
        const qaId = params.get("qaId");
        
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
    
    // 질문 전송 함수 (병렬 요청 방식)
    const sendQuestion = async (questionText) => {
        setIsLoading(true);
        setServerResponseReceived(false);

        const newQaEntry = { 
            question: questionText,
            answer: "답변을 불러오는 중...",
            localAnswer: "로컬 답변을 불러오는 중...",
            globalAnswer: "글로벌 답변을 불러오는 중...",
            confidence: null,
            localConfidence: null,
            globalConfidence: null,
            actionButtonVisible: false, // 그래프 버튼 숨김
            relatedQuestionsVisible: false, // 관련 질문 숨김
        };
        
        // 새 질문-답변 추가
        setQaList((prevQaList) => [...prevQaList, newQaEntry]);
        setNewQuestion(""); // 질문 입력란 초기화
        
        // 각 방식별 서버 요청 함수
        const fetchLocalResponse = () => {
            return fetch("http://localhost:5000/run-query", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    page_id: currentPageId,
                    message: questionText,
                    resMethod: "local",
                    resType: "text"
                })
            }).then(response => response.json());
        };
        
        const fetchGlobalResponse = () => {
            return fetch("http://localhost:5000/run-query", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify({
                    page_id: currentPageId,
                    message: questionText,
                    resMethod: "global",
                    resType: "text"
                })
            }).then(response => response.json());
        };

        try {
            // 두 요청을 병렬로 실행
            const [localData, globalData] = await Promise.all([
                fetchLocalResponse()
            ]);
            
            // 각 응답 확인 및 통합 처리
            const localAnswer = localData.result || "서버에서 로컬 응답을 받지 못했습니다.";
            const globalAnswer = "서버에서 글로벌 응답을 받지 못했습니다.";
            
            // 엔티티와 관계는 로컬 데이터에서 가져옴
            const newEntities = localData.entities ? localData.entities.join(',') : "";
            const newRelationships = localData.relationships ? localData.relationships.join(',') : "";
            
            // 응답 업데이트
            updateLastAnswer(localAnswer, globalAnswer, newEntities, newRelationships);
            setEntities(newEntities);
            setRelationships(newRelationships);
            setServerResponseReceived(true);
            
            // 기존 그래프 데이터 캐시 초기화
            graphDataCacheRef.current = {};
            
            // 그래프 및 관련 질문 보이기
            setQaList(prevQaList => {
                const updatedList = [...prevQaList];
                updatedList[updatedList.length - 1].actionButtonVisible = true;
                updatedList[updatedList.length - 1].relatedQuestionsVisible = true;
                return updatedList;
            });
            
            // 대화 히스토리에 저장
            saveToQAHistory(questionText, localAnswer, globalAnswer, newEntities, newRelationships);
            
        } catch (error) {
            console.error("네트워크 오류:", error);
            const errorMessage = "네트워크 오류가 발생했습니다. 다시 시도해주세요.";
            updateLastAnswer(errorMessage, errorMessage, "", "");
            setServerResponseReceived(false);
        } finally {
            setIsLoading(false);
        }
    };

    // QA 히스토리에 저장하는 함수
    const saveToQAHistory = (question, localAnswer, globalAnswer, entities, relationships) => {
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
            globalConfidence: 90
        };
        
        if (qaId) {
            // 기존 대화에 추가
            const existingQA = qaHistory.find(qa => qa.id === qaId);
            if (existingQA) {
                const updatedConversations = [...(existingQA.conversations || []), newConversation];
                addQA({
                    ...existingQA,
                    conversations: updatedConversations,
                    question: question, // 가장 최근 질문으로 제목 업데이트
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
            
            // URL 업데이트 (새 qaId)
            navigate(`/chat?qaId=${newQAId}`, { replace: true });
        }
    };

    // 최신 질문의 답변 업데이트
    const updateLastAnswer = (localAnswer, globalAnswer, newEntities, newRelationships) => {
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
                relationships: newRelationships
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
        
        if (!entities || !relationships) {
            console.error("엔티티 또는 관계 데이터가 없습니다.");
            alert("엔티티 또는 관계 데이터가 없습니다. 대화를 완료한 후 다시 시도해주세요.");
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
            
            // API 호출
            const generateResponse = await fetch("http://localhost:5000/generate-graph", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    page_id: currentPageId,
                    entities: entities,
                    relationships: relationships
                })
            });

            // API 응답 처리
            const generateData = await generateResponse.json();

            if (!generateResponse.ok) {
                throw new Error(`그래프 생성 실패: ${generateData.error || "알 수 없는 오류"}`);
            }
            
            console.log("그래프 생성 API 응답:", generateData);
            
            // 서버에서 파일 생성이 완료될 때까지 대기 (최소 1초)
            await new Promise(resolve => setTimeout(resolve, 1500));
            
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
                throw new Error(`HTTP 에러! 상태: ${jsonResponse.status}, ${jsonResponse.statusText}`);
            }

            const jsonData = await jsonResponse.json();
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

    // 질문을 입력 후 전송
    const handleSendQuestion = () => {
        if (newQuestion.trim() && !isLoading) {
            sendQuestion(newQuestion.trim());
        }
    };
    
    // 사이드바 토글 함수
    const toggleSidebar = () => {
        setIsSidebarOpen(!isSidebarOpen);
    };
    
    return (
        <div className={`chat-page-container ${showGraph ? "with-graph" : ""}`}>
            <Sidebar 
                isSidebarOpen={isSidebarOpen} 
                toggleSidebar={toggleSidebar} 
            />
            
            <div className={`chat-container ${showGraph ? "shift-left" : ""} ${isSidebarOpen ? "sidebar-open" : ""}`}>
                <div className="chat-messages">
                    {qaList.map((qa, index) => (
                        <ChatMessage 
                            key={index} 
                            qa={qa} 
                            index={index} 
                            handleShowGraph={handleShowGraph} 
                        />
                    ))}
                </div>

                <ChatInput 
                    newQuestion={newQuestion} 
                    setNewQuestion={setNewQuestion} 
                    handleSendQuestion={handleSendQuestion} 
                    isLoading={isLoading} 
                />

                {showGraph && graphData && (
                    <div className="graph-container">
                        <button className="close-graph" onClick={handleCloseGraph}>닫기</button>
                        <NetworkChart data={graphData} />
                    </div>
                )}
            </div>
        </div>
    );
}

export default ChatPage;