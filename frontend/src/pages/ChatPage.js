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
    const { currentPageId } = usePageContext();
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
        console.log("현재 페이지 ID:", currentPageId);

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
    
    // 질문 전송 함수
    const sendQuestion = async (questionText) => {
        setIsLoading(true);
        setServerResponseReceived(false);

        const newQaEntry = { 
            question: questionText,
            answer: "답변을 불러오는 중...", 
            confidence: null,
            actionButtonVisible: false, // 그래프 버튼 숨김
            relatedQuestionsVisible: false, // 관련 질문 숨김
        };
        
        // 새 질문-답변 추가
        setQaList((prevQaList) => [...prevQaList, newQaEntry]);
        setNewQuestion(""); // 질문 입력란 초기화

        try {
            const response = await fetch("http://localhost:5000/run-query", {
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
            });

            const data = await response.json();

            if (response.ok) {
                const answer = data.result || "서버에서 응답을 받지 못했습니다.";
                const newEntities = data.entities.join(',');
                const newRelationships = data.relationships.join(',');
                
                updateLastAnswer(answer, newEntities, newRelationships);
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
                saveToQAHistory(questionText, answer, newEntities, newRelationships);

            } else {
                updateLastAnswer(`서버 오류: ${data.error || '알 수 없는 오류'}`);
                setServerResponseReceived(false);
            }
        } catch (error) {
            console.error("네트워크 오류:", error);
            updateLastAnswer("네트워크 오류가 발생했습니다. 다시 시도해주세요.");
            setServerResponseReceived(false);
        } finally {
            setIsLoading(false);
        }
    };

    // QA 히스토리에 저장하는 함수
    const saveToQAHistory = (question, answer, entities, relationships) => {
        const params = new URLSearchParams(location.search);
        const qaId = params.get("qaId");
        
        // 현재 날짜/시간
        const timestamp = new Date().toISOString();
        
        // 새 대화 항목
        const newConversation = {
            question,
            answer,
            timestamp,
            entities,
            relationships,
            actionButtonVisible: true,
            relatedQuestionsVisible: true,
            confidence: 99
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
    const updateLastAnswer = (answer, newEntities, newRelationships) => {
        setQaList((prevQaList) => {
            if (prevQaList.length === 0) return prevQaList;

            const newList = [...prevQaList];
            const lastIndex = newList.length - 1;
            newList[lastIndex] = {
                ...newList[lastIndex],
                answer: answer || "답변을 불러오는 중...",
                confidence: 99,  // 정확도 나중에 설정해주기
                entities: newEntities,
                relationships: newRelationships
            };
            return newList;
        });
    };

    // 그래프 로드 함수
    const handleShowGraph = async (e, index) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }

        if (!serverResponseReceived) {
            console.log("서버 응답을 기다리는 중입니다.");
            return; // 서버 응답이 아직 없으면 그래프를 로드하지 않음
        }

        // 캐시된 그래프 데이터 확인
        const cacheKey = `${entities}-${relationships}`;
        if (graphDataCacheRef.current[cacheKey]) {
            setGraphData(graphDataCacheRef.current[cacheKey]);
            setShowGraph(true);
            return;
        }

        try {
            console.log("그래프 데이터 로딩 시작");
            setIsLoading(true);

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

            const generateData = await generateResponse.json();

            if (!generateResponse.ok) {
                throw new Error(`Graph generation failed: ${generateData.error || "Unknown error"}`);
            }
            
            // 서브 그래프 그리기 위한 json 파일 로드
            const response = await fetch("./json/answer_graphml_data.json", {
                headers: {
                    "Cache-Control": "no-cache"
                }
            });
    
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("그래프 데이터 로드 성공:", data);

            // 그래프 데이터 캐시
            graphDataCacheRef.current[cacheKey] = data;

            setGraphData(data);
            setShowGraph(true);
        } catch (error) {
            console.error("그래프 데이터 로드 실패:", error);
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