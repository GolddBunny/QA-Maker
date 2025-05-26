import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
    collection, 
    doc, 
    getDocs, 
    addDoc, 
    updateDoc, 
    deleteDoc, 
    query, 
    orderBy, 
    onSnapshot,
    where
} from 'firebase/firestore';
import { db } from '../firebase/sdk'; // Firebase 설정 파일 경로에 맞게 수정

// QA 히스토리 컨텍스트 생성
const QAHistoryContext = createContext();

// QA 히스토리 제공자 컴포넌트
export function QAHistoryProvider({ children }) {
    const [qaHistory, setQaHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Firestore에서 QA 히스토리 실시간 로드
    useEffect(() => {
        const loadQAHistory = () => {
            try {
                // QA 히스토리 컬렉션 참조
                const qaHistoryRef = collection(db, 'qaHistory');
                
                // 타임스탬프 기준으로 내림차순 정렬하여 쿼리
                const q = query(qaHistoryRef, orderBy('timestamp', 'desc'));
                
                // 실시간 리스너 설정
                const unsubscribe = onSnapshot(q, 
                    (snapshot) => {
                        const qaList = [];
                        snapshot.forEach((doc) => {
                            qaList.push({
                                id: doc.id,
                                firestoreId: doc.id, // Firestore 문서 ID 저장
                                ...doc.data()
                            });
                        });
                        
                        setQaHistory(qaList);
                        setLoading(false);
                        setError(null);
                    },
                    (err) => {
                        console.error("QA 히스토리 로드 실패:", err);
                        setError(err.message);
                        setLoading(false);
                    }
                );

                // 컴포넌트 언마운트 시 리스너 해제
                return unsubscribe;
            } catch (err) {
                console.error("QA 히스토리 로드 설정 실패:", err);
                setError(err.message);
                setLoading(false);
            }
        };

        const unsubscribe = loadQAHistory();
        
        // 클린업 함수
        return () => {
            if (typeof unsubscribe === 'function') {
                unsubscribe();
            }
        };
    }, []);

    // QA 항목 추가 또는 업데이트 함수
    const addQA = async (newQA) => {
        try {
            const qaHistoryRef = collection(db, 'qaHistory');
            
            // 기존 항목인지 확인 (id 기준)
            const existingQA = qaHistory.find(qa => qa.id === newQA.id);
            
            if (existingQA && existingQA.firestoreId) {
                // 기존 항목 업데이트
                const docRef = doc(db, 'qaHistory', existingQA.firestoreId);
                await updateDoc(docRef, {
                    ...newQA,
                    updatedAt: new Date().toISOString()
                });
                console.log("QA 항목 업데이트 완료:", newQA.id);
            } else {
                // 새 항목 추가
                const docRef = await addDoc(qaHistoryRef, {
                    ...newQA,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                });
                console.log("새 QA 항목 추가 완료:", docRef.id);
            }
        } catch (err) {
            console.error("QA 항목 저장 실패:", err);
            setError(err.message);
            throw err; // 에러를 다시 던져서 호출하는 곳에서 처리할 수 있도록
        }
    };

    // QA 항목 삭제 함수
    const deleteQA = async (qaId) => {
        try {
            // qaId로 해당 항목 찾기
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                await deleteDoc(docRef);
                console.log("QA 항목 삭제 완료:", qaId);
            } else {
                console.warn("삭제할 QA 항목을 찾을 수 없습니다:", qaId);
            }
        } catch (err) {
            console.error("QA 항목 삭제 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // QA 항목에 headline 업데이트 함수
    const updateQAHeadlines = async (qaId, conversationIndex, headlines) => {
        try {
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const updatedConversations = [...(qaItem.conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        headlines: headlines,
                        selectedHeadline: headlines && headlines.length > 0 ? headlines[0] : ''
                    };
                    
                    const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                    await updateDoc(docRef, {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    });
                    
                    console.log("Headlines 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("Headlines 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 선택된 headline 업데이트 함수
    const updateSelectedHeadline = async (qaId, conversationIndex, headline) => {
        try {
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const updatedConversations = [...(qaItem.conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        selectedHeadline: headline
                    };
                    
                    const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                    await updateDoc(docRef, {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    });
                    
                    console.log("선택된 headline 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("선택된 headline 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 소스 URL 업데이트 함수
    const updateQASources = async (qaId, conversationIndex, sources) => {
        try {
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const updatedConversations = [...(qaItem.conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        sources: sources || []
                    };
                    
                    const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                    await updateDoc(docRef, {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    });
                    
                    console.log("소스 URL 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("소스 URL 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 특정 페이지의 QA 히스토리만 가져오는 함수 (필요시 사용)
    const getQAHistoryByPageId = async (pageId) => {
        try {
            const qaHistoryRef = collection(db, 'qaHistory');
            const q = query(
                qaHistoryRef, 
                where('pageId', '==', pageId),
                orderBy('timestamp', 'desc')
            );
            
            const snapshot = await getDocs(q);
            const qaList = [];
            
            snapshot.forEach((doc) => {
                qaList.push({
                    id: doc.id,
                    firestoreId: doc.id,
                    ...doc.data()
                });
            });
            
            return qaList;
        } catch (err) {
            console.error("페이지별 QA 히스토리 로드 실패:", err);
            setError(err.message);
            return [];
        }
    };

    // 컨텍스트 값 설정
    const contextValue = {
        qaHistory,
        loading,
        error,
        addQA,
        deleteQA,
        updateQAHeadlines,
        updateSelectedHeadline,
        updateQASources,
        getQAHistoryByPageId
    };

    return (
        <QAHistoryContext.Provider value={contextValue}>
            {children}
        </QAHistoryContext.Provider>
    );
}

// QA 히스토리 컨텍스트 사용 훅
export function useQAHistoryContext() {
    const context = useContext(QAHistoryContext);
    
    if (!context) {
        throw new Error('useQAHistoryContext must be used within a QAHistoryProvider');
    }
    
    return context;
}