import React, { createContext, useContext, useState, useEffect } from 'react';

// QA 히스토리 컨텍스트 생성
const QAHistoryContext = createContext();

// QA 히스토리 제공자 컴포넌트
export function QAHistoryProvider({ children }) {
    // 로컬 스토리지에서 QA 히스토리 로드
    const [qaHistory, setQaHistory] = useState(() => {
        const savedHistory = localStorage.getItem('qaHistory');
        return savedHistory ? JSON.parse(savedHistory) : [];
    });
    
    // QA 히스토리가 변경될 때마다 로컬 스토리지에 저장
    useEffect(() => {
        localStorage.setItem('qaHistory', JSON.stringify(qaHistory));
    }, [qaHistory]);
    
    // QA 항목 추가 또는 업데이트 함수
    const addQA = (newQA) => {
        setQaHistory(prevHistory => {
            const existingIndex = prevHistory.findIndex(qa => qa.id === newQA.id);
            
            if (existingIndex >= 0) {
                // 기존 항목 업데이트
                const updatedHistory = [...prevHistory];
                updatedHistory[existingIndex] = newQA;
                return updatedHistory;
            } else {
                // 새 항목 추가
                return [...prevHistory, newQA];
            }
        });
    };
    
    // QA 항목 삭제 함수
    const deleteQA = (qaId) => {
        setQaHistory(prevHistory => prevHistory.filter(qa => qa.id !== qaId));
    };
    
    // QA 항목에 headline 업데이트 함수
    const updateQAHeadlines = (qaId, conversationIndex, headlines) => {
        setQaHistory(prevHistory => {
            const updatedHistory = [...prevHistory];
            const qaIndex = updatedHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex >= 0 && updatedHistory[qaIndex].conversations && 
                updatedHistory[qaIndex].conversations[conversationIndex]) {
                updatedHistory[qaIndex].conversations[conversationIndex].headlines = headlines;
                updatedHistory[qaIndex].conversations[conversationIndex].selectedHeadline = 
                    headlines && headlines.length > 0 ? headlines[0] : '';
            }
            
            return updatedHistory;
        });
    };
    
    // 선택된 headline 업데이트 함수
    const updateSelectedHeadline = (qaId, conversationIndex, headline) => {
        setQaHistory(prevHistory => {
            const updatedHistory = [...prevHistory];
            const qaIndex = updatedHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex >= 0 && updatedHistory[qaIndex].conversations && 
                updatedHistory[qaIndex].conversations[conversationIndex]) {
                updatedHistory[qaIndex].conversations[conversationIndex].selectedHeadline = headline;
            }
            
            return updatedHistory;
        });
    };
    
    // 소스 URL 업데이트 함수
    const updateQASources = (qaId, conversationIndex, sources) => {
        setQaHistory(prevHistory => {
            const updatedHistory = [...prevHistory];
            const qaIndex = updatedHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex >= 0 && updatedHistory[qaIndex].conversations && 
                updatedHistory[qaIndex].conversations[conversationIndex]) {
                updatedHistory[qaIndex].conversations[conversationIndex].sources = sources || [];
            }
            
            return updatedHistory;
        });
    };
    
    // 컨텍스트 값 설정
    const contextValue = {
        qaHistory,
        addQA,
        deleteQA,
        updateQAHeadlines,
        updateSelectedHeadline,
        updateQASources
    };
    
    return (
        <QAHistoryContext.Provider value={contextValue}>
            {children}
        </QAHistoryContext.Provider>
    );
}

// QA 히스토리 컨텍스트 사용 훅
export function useQAHistoryContext() {
    return useContext(QAHistoryContext);
}