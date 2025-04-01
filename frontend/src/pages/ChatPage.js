import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../styles/ChatPage.css";
import NetworkChart from "../components/charts/NetworkChart";
import ChatMessage from "../components/chat/ChatMessage";
import ChatInput from "../components/chat/ChatInput";
import { usePageContext } from "../utils/PageContext";

/* 채팅 페이지 */

function ChatPage() {
    const { currentPageId } = usePageContext();
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
    // 그래프 데이터 캐시를 위한 참조
    const graphDataCacheRef = useRef({});

    // 페이지 로드 시 초기 질문 처리
    useEffect(() => {
        console.log("현재 페이지 ID:", currentPageId);

        const params = new URLSearchParams(location.search);
        const initialQuestion = params.get("question");
    
        if (initialQuestion && !hasSentInitialQuestion.current) {
            setNewQuestion(initialQuestion);
            setTimeout(() => {
                sendQuestion(initialQuestion);
            }, 500);
            hasSentInitialQuestion.current = true;
        }
    }, [location.search]);
    
    // 질문 전송 함수
    const sendQuestion = async (questionText) => {
        setIsLoading(true);
        setServerResponseReceived(false);

        const newQaEntry = { question: questionText,
             answer: "답변을 불러오는 중...", 
             confidence: null,
             actionButtonVisible: false, // 그래프 버튼 숨김
            relatedQuestionsVisible: false, // 관련 질문 숨김
            };
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
                updateLastAnswer(data.result || "서버에서 응답을 받지 못했습니다.");
                setEntities(data.entities.join(','));
                setRelationships(data.relationships.join(','));
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

    // 최신 질문의 답변 업데이트
    const updateLastAnswer = (answer) => {
        setQaList((prevQaList) => {
            if (prevQaList.length === 0) return prevQaList;

            const newList = [...prevQaList];
            const lastIndex = newList.length - 1;
            newList[lastIndex] = {
                ...newList[lastIndex],
                answer: answer || "답변을 불러오는 중...",
                confidence: 99  // 정확도 나중에 설정해주기
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

    // 그래프 닫기 함수 수정
    const handleCloseGraph = () => {
        setShowGraph(false);
    };

    // 질문을 입력 후 전송
    const handleSendQuestion = () => {
        if (newQuestion.trim() && !isLoading) {
            sendQuestion(newQuestion.trim());
        }
    };
    
    return (
        <div className={`chat-container ${showGraph ? "shift-left" : ""}`}>
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
                    <button className="close-graph-button" onClick={handleCloseGraph}>×</button>
                    <NetworkChart data={graphData} />
                </div>
            )}
        </div>
    );
}

export default ChatPage;