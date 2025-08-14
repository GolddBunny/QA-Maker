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
import { db } from '../firebase/sdk';

// QA 히스토리 컨텍스트 생성
const QAHistoryContext = createContext();

// Firestore에 저장하기 전에 undefined 값을 제거하는 유틸리티 함수
const cleanDataForFirestore = (data) => {
    if (data === null || data === undefined) {
        return null;
    }
    
    if (Array.isArray(data)) {
        return data.map(item => cleanDataForFirestore(item)).filter(item => item !== undefined);
    }
    
    if (typeof data === 'object') {
        const cleanedData = {};
        Object.keys(data).forEach(key => {
            const value = cleanDataForFirestore(data[key]);
            if (value !== undefined) {
                cleanedData[key] = value;
            }
        });
        return cleanedData;
    }
    
    return data;
};

// QA 히스토리 제공자 컴포넌트
export function QAHistoryProvider({ children }) {
    const [qaHistory, setQaHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // localStorage에서 QA 히스토리 로드
    const loadFromLocalStorage = () => {
        try {
            const storedQAHistory = localStorage.getItem('qaHistory');
            if (storedQAHistory) {
                const parsedHistory = JSON.parse(storedQAHistory);
                // 타임스탬프 기준으로 내림차순 정렬
                const sortedHistory = parsedHistory.sort((a, b) => 
                    new Date(b.timestamp) - new Date(a.timestamp)
                );
                return sortedHistory;
            }
            return [];
        } catch (err) {
            console.error("localStorage에서 QA 히스토리 로드 실패:", err);
            return [];
        }
    };

    // localStorage에 QA 히스토리 저장
    const saveToLocalStorage = (history) => {
        try {
            localStorage.setItem('qaHistory', JSON.stringify(history));
        } catch (err) {
            console.error("localStorage 저장 실패:", err);
            setError(err.message);
        }
    };

    // Firestore에서 QA 히스토리 실시간 로드 (관리자용)
    const loadFromFirestore = () => {
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
                    
                    return qaList;
                },
                (err) => {
                    console.error("Firestore QA 히스토리 로드 실패:", err);
                    return [];
                }
            );

            return unsubscribe;
        } catch (err) {
            console.error("Firestore QA 히스토리 로드 설정 실패:", err);
            return () => {};
        }
    };

    // 컴포넌트 마운트 시 localStorage에서 로드
    useEffect(() => {
        const localHistory = loadFromLocalStorage();
        setQaHistory(localHistory);
        setLoading(false);
    }, []);

    // localStorage에 QA 항목 추가 또는 업데이트
    const addQAToLocalStorage = (newQA) => {
        try {
            const currentHistory = loadFromLocalStorage();
            
            // 기존 항목인지 확인 (id 기준)
            const existingIndex = currentHistory.findIndex(qa => qa.id === newQA.id);
            
            let updatedHistory;
            if (existingIndex !== -1) {
                // 기존 항목 업데이트 (정확도와 관련 질문 포함)
                updatedHistory = [...currentHistory];
                updatedHistory[existingIndex] = {
                    ...updatedHistory[existingIndex],
                    ...newQA,
                    conversations: (newQA.conversations || []).map(conversation => ({
                        ...conversation,
                        // 정확도 기본값
                        confidence: conversation.confidence || 0.0,
                        localConfidence: conversation.localConfidence || 0.0,
                        globalConfidence: conversation.globalConfidence || 0.0,
                        // 관련 질문 기본값
                        relatedQuestions: conversation.relatedQuestions || [],
                        relatedQuestionsVisible: conversation.relatedQuestionsVisible !== undefined 
                            ? conversation.relatedQuestionsVisible 
                            : false,
                        // 기타 필드 기본값
                        headlines: conversation.headlines || [],
                        sources: conversation.sources || [],
                        actionButtonVisible: conversation.actionButtonVisible !== undefined 
                            ? conversation.actionButtonVisible 
                            : true
                    })),
                    updatedAt: new Date().toISOString()
                };
                console.log("localStorage QA 항목 업데이트 완료:", newQA.id);
            } else {
                // 새 항목 추가 (정확도와 관련 질문 포함)
                const newQAWithTimestamp = {
                    ...newQA,
                    conversations: (newQA.conversations || []).map(conversation => ({
                        ...conversation,
                        // 정확도 기본값
                        confidence: conversation.confidence || 0.0,
                        localConfidence: conversation.localConfidence || 0.0,
                        globalConfidence: conversation.globalConfidence || 0.0,
                        // 관련 질문 기본값
                        relatedQuestions: conversation.relatedQuestions || [],
                        relatedQuestionsVisible: conversation.relatedQuestionsVisible !== undefined 
                            ? conversation.relatedQuestionsVisible 
                            : false,
                        // 기타 필드 기본값
                        headlines: conversation.headlines || [],
                        sources: conversation.sources || [],
                        actionButtonVisible: conversation.actionButtonVisible !== undefined 
                            ? conversation.actionButtonVisible 
                            : true
                    })),
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                };
                updatedHistory = [newQAWithTimestamp, ...currentHistory];
                console.log("localStorage 새 QA 항목 추가 완료:", newQA.id);
            }
            
            // localStorage에 저장
            saveToLocalStorage(updatedHistory);
            
            // 상태 업데이트
            setQaHistory(updatedHistory);
            
        } catch (err) {
            console.error("localStorage QA 항목 저장 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // Firebase에 QA 항목 추가 또는 업데이트 (관리자용)
    const addQAToFirestore = async (newQA) => {
        try {
            const qaHistoryRef = collection(db, 'qaHistory');
            
            // undefined 값 제거 및 기본값 설정 (정확도와 관련 질문 포함)
            const cleanedQA = cleanDataForFirestore({
                ...newQA,
                // 필수 필드들에 대한 기본값 설정
                id: newQA.id || '',
                pageId: newQA.pageId || '',
                question: newQA.question || '',
                answer: newQA.answer || '',
                timestamp: newQA.timestamp || new Date().toISOString(),
                conversations: (newQA.conversations || []).map(conversation => ({
                    ...conversation,
                    // 정확도 기본값
                    confidence: conversation.confidence || 0.0,
                    localConfidence: conversation.localConfidence || 0.0,
                    globalConfidence: conversation.globalConfidence || 0.0,
                    // 관련 질문 기본값
                    relatedQuestions: conversation.relatedQuestions || [],
                    relatedQuestionsVisible: conversation.relatedQuestionsVisible !== undefined 
                        ? conversation.relatedQuestionsVisible 
                        : false,
                    // 기타 필드 기본값
                    headlines: conversation.headlines || [],
                    sources: conversation.sources || [],
                    actionButtonVisible: conversation.actionButtonVisible !== undefined 
                        ? conversation.actionButtonVisible 
                        : true
                })),
                sources: newQA.sources || [],
                headlines: newQA.headlines || [],
                selectedHeadline: newQA.selectedHeadline || ''
            });
            
            // 기존 항목인지 확인 (id 기준)
            const existingQA = qaHistory.find(qa => qa.id === newQA.id);
            
            if (existingQA && existingQA.firestoreId) {
                // 기존 항목 업데이트
                const docRef = doc(db, 'qaHistory', existingQA.firestoreId);
                const updateData = {
                    ...cleanedQA,
                    updatedAt: new Date().toISOString()
                };
                await updateDoc(docRef, cleanDataForFirestore(updateData));
                console.log("Firestore QA 항목 업데이트 완료:", newQA.id);
                return existingQA.firestoreId; // 기존 firestoreId 반환
            } else {
                // 새 항목 추가
                const addData = {
                    ...cleanedQA,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                };
                const docRef = await addDoc(qaHistoryRef, cleanDataForFirestore(addData));
                console.log("Firestore 새 QA 항목 추가 완료:", docRef.id);
                return docRef.id; // 새로 생성된 firestoreId 반환
            }
        } catch (err) {
            console.error("Firestore QA 항목 저장 실패:", err);
            console.error("저장하려던 데이터:", newQA);
            setError(err.message);
            throw err;
        }
    };

    // 통합 QA 추가 함수 (ChatPage에서는 localStorage만, 관리자 페이지에서는 Firebase도)
    const addQA = async (newQA, saveToFirestore = false) => {
        // localStorage에는 항상 저장
        addQAToLocalStorage(newQA);
        
        // Firebase에는 필요시에만 저장 (관리자 페이지용)
        if (saveToFirestore) {
            try {
                const firestoreId = await addQAToFirestore(newQA);
                console.log("받은 firestoreId:", firestoreId);
                
                if (firestoreId) {
                    // localStorage 업데이트
                    const currentHistory = loadFromLocalStorage();
                    const qaIndex = currentHistory.findIndex(qa => qa.id === newQA.id);
                    if (qaIndex !== -1) {
                        currentHistory[qaIndex].firestoreId = firestoreId;
                        saveToLocalStorage(currentHistory);
                        console.log("localStorage에 firestoreId 저장 완료:", newQA.id, "->", firestoreId);
                    }
                    
                    // 메모리 상태 즉시 업데이트 (중요!)
                    setQaHistory(prevHistory => {
                        const updatedHistory = [...prevHistory];
                        const memoryQaIndex = updatedHistory.findIndex(qa => qa.id === newQA.id);
                        if (memoryQaIndex !== -1) {
                            updatedHistory[memoryQaIndex] = {
                                ...updatedHistory[memoryQaIndex],
                                firestoreId: firestoreId
                            };
                            console.log("메모리에 firestoreId 저장 완료:", newQA.id, "->", firestoreId);
                        }
                        return updatedHistory;
                    });
                }
            } catch (error) {
                console.error("Firebase 저장 중 오류:", error);
            }
        }
    };

    // localStorage에서 QA 항목 삭제
    const deleteQAFromLocalStorage = (qaId) => {
        try {
            const currentHistory = loadFromLocalStorage();
            const updatedHistory = currentHistory.filter(qa => qa.id !== qaId);
            
            saveToLocalStorage(updatedHistory);
            setQaHistory(updatedHistory);
            
            console.log("localStorage QA 항목 삭제 완료:", qaId);
        } catch (err) {
            console.error("localStorage QA 항목 삭제 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // Firebase에서 QA 항목 삭제 (관리자용)
    const deleteQAFromFirestore = async (qaId) => {
        try {
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                await deleteDoc(docRef);
                console.log("Firestore QA 항목 삭제 완료:", qaId);
            } else {
                console.warn("삭제할 Firestore QA 항목을 찾을 수 없습니다:", qaId);
            }
        } catch (err) {
            console.error("Firestore QA 항목 삭제 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 통합 QA 삭제 함수
    const deleteQA = async (qaId, deleteFromFirestore = false) => {
        // localStorage에서는 항상 삭제
        deleteQAFromLocalStorage(qaId);
        
        // Firebase에서는 필요시에만 삭제 (관리자 페이지용)
        if (deleteFromFirestore) {
            await deleteQAFromFirestore(qaId);
        }
    };

    // QA 항목에 headline 업데이트 함수 (localStorage용)
    const updateQAHeadlinesInLocalStorage = (qaId, conversationIndex, headlines) => {
        try {
            const currentHistory = loadFromLocalStorage();
            const qaIndex = currentHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex !== -1) {
                const updatedHistory = [...currentHistory];
                const updatedConversations = [...(updatedHistory[qaIndex].conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        headlines: headlines || [],
                        selectedHeadline: headlines && headlines.length > 0 ? headlines[0] : ''
                    };
                    
                    updatedHistory[qaIndex] = {
                        ...updatedHistory[qaIndex],
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    
                    saveToLocalStorage(updatedHistory);
                    setQaHistory(updatedHistory);
                    
                    console.log("localStorage Headlines 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("localStorage Headlines 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // Firebase headline 업데이트 (관리자용)
    const updateQAHeadlinesInFirestore = async (qaId, conversationIndex, headlines) => {
        try {
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const updatedConversations = [...(qaItem.conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        headlines: headlines || [],
                        selectedHeadline: headlines && headlines.length > 0 ? headlines[0] : ''
                    };
                    
                    const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                    const updateData = {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    await updateDoc(docRef, cleanDataForFirestore(updateData));
                    
                    console.log("Firestore Headlines 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("Firestore Headlines 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 통합 headline 업데이트 함수
    const updateQAHeadlines = async (qaId, conversationIndex, headlines, updateFirestore = false) => {
        // localStorage는 항상 업데이트
        updateQAHeadlinesInLocalStorage(qaId, conversationIndex, headlines);
        
        // Firebase는 필요시에만 업데이트
        if (updateFirestore) {
            await updateQAHeadlinesInFirestore(qaId, conversationIndex, headlines);
        }
    };

    // 선택된 headline 업데이트 (localStorage용)
    const updateSelectedHeadlineInLocalStorage = (qaId, conversationIndex, headline) => {
        try {
            const currentHistory = loadFromLocalStorage();
            const qaIndex = currentHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex !== -1) {
                const updatedHistory = [...currentHistory];
                const updatedConversations = [...(updatedHistory[qaIndex].conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        selectedHeadline: headline || ''
                    };
                    
                    updatedHistory[qaIndex] = {
                        ...updatedHistory[qaIndex],
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    
                    saveToLocalStorage(updatedHistory);
                    setQaHistory(updatedHistory);
                    
                    console.log("localStorage 선택된 headline 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("localStorage 선택된 headline 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // Firebase 선택된 headline 업데이트 (관리자용)
    const updateSelectedHeadlineInFirestore = async (qaId, conversationIndex, headline) => {
        try {
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const updatedConversations = [...(qaItem.conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        selectedHeadline: headline || ''
                    };
                    
                    const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                    const updateData = {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    await updateDoc(docRef, cleanDataForFirestore(updateData));
                    
                    console.log("Firestore 선택된 headline 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("Firestore 선택된 headline 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 통합 선택된 headline 업데이트 함수
    const updateSelectedHeadline = async (qaId, conversationIndex, headline, updateFirestore = false) => {
        // localStorage는 항상 업데이트
        updateSelectedHeadlineInLocalStorage(qaId, conversationIndex, headline);
        
        // Firebase는 필요시에만 업데이트
        if (updateFirestore) {
            await updateSelectedHeadlineInFirestore(qaId, conversationIndex, headline);
        }
    };

    // 소스 URL 업데이트 (localStorage용)
    const updateQASourcesInLocalStorage = (qaId, conversationIndex, sources) => {
        try {
            const currentHistory = loadFromLocalStorage();
            const qaIndex = currentHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex !== -1) {
                const updatedHistory = [...currentHistory];
                const updatedConversations = [...(updatedHistory[qaIndex].conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        sources: sources || []
                    };
                    
                    updatedHistory[qaIndex] = {
                        ...updatedHistory[qaIndex],
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    
                    saveToLocalStorage(updatedHistory);
                    setQaHistory(updatedHistory);
                    
                    console.log("localStorage 소스 URL 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("localStorage 소스 URL 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // Firebase 소스 URL 업데이트 (관리자용)
    const updateQASourcesInFirestore = async (qaId, conversationIndex, sources) => {
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
                    const updateData = {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    await updateDoc(docRef, cleanDataForFirestore(updateData));
                    
                    console.log("Firestore 소스 URL 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("Firestore 소스 URL 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 통합 소스 URL 업데이트 함수
    const updateQASources = async (qaId, conversationIndex, sources, updateFirestore = false) => {
        // localStorage는 항상 업데이트
        updateQASourcesInLocalStorage(qaId, conversationIndex, sources);
        
        // Firebase는 필요시에만 업데이트
        if (updateFirestore) {
            await updateQASourcesInFirestore(qaId, conversationIndex, sources);
        }
    };

    // 특정 페이지의 QA 히스토리만 가져오는 함수 (localStorage용)
    const getQAHistoryByPageIdFromLocalStorage = (pageId) => {
        try {
            const currentHistory = loadFromLocalStorage();
            return currentHistory.filter(qa => qa.pageId === pageId);
        } catch (err) {
            console.error("localStorage 페이지별 QA 히스토리 로드 실패:", err);
            setError(err.message);
            return [];
        }
    };

    // 특정 페이지의 QA 히스토리만 가져오는 함수 (Firebase용)
    const getQAHistoryByPageIdFromFirestore = async (pageId) => {
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
            console.error("Firestore 페이지별 QA 히스토리 로드 실패:", err);
            setError(err.message);
            return [];
        }
    };

    // 통합 페이지별 QA 히스토리 가져오기 함수
    const getQAHistoryByPageId = async (pageId, fromFirestore = false) => {
        if (fromFirestore) {
            return await getQAHistoryByPageIdFromFirestore(pageId);
        } else {
            return getQAHistoryByPageIdFromLocalStorage(pageId);
        }
    };

    // Firebase에서 모든 QA 히스토리 가져오기 (관리자용)
    const loadAllFromFirestore = async () => {
        try {
            setLoading(true);
            const unsubscribe = loadFromFirestore();
            
            // 실시간 리스너가 데이터를 받아오면 상태 업데이트
            // 이 부분은 실제 구현에서 onSnapshot 콜백 내에서 처리됩니다
            
            return unsubscribe;
        } catch (err) {
            console.error("Firebase QA 히스토리 로드 실패:", err);
            setError(err.message);
            setLoading(false);
            return () => {};
        }
    };

    // 4. 정확도 업데이트 함수 추가 (localStorage용)
    const updateQAConfidenceInLocalStorage = (qaId, conversationIndex, confidenceData) => {
        try {
            const currentHistory = loadFromLocalStorage();
            const qaIndex = currentHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex !== -1) {
                const updatedHistory = [...currentHistory];
                const updatedConversations = [...(updatedHistory[qaIndex].conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        confidence: confidenceData.confidence !== undefined ? confidenceData.confidence : updatedConversations[conversationIndex].confidence,
                        localConfidence: confidenceData.localConfidence !== undefined ? confidenceData.localConfidence : updatedConversations[conversationIndex].localConfidence,
                        globalConfidence: confidenceData.globalConfidence !== undefined ? confidenceData.globalConfidence : updatedConversations[conversationIndex].globalConfidence,
                    };
                    
                    updatedHistory[qaIndex] = {
                        ...updatedHistory[qaIndex],
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    
                    saveToLocalStorage(updatedHistory);
                    setQaHistory(updatedHistory);
                    
                    console.log("localStorage 정확도 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("localStorage 정확도 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 5. 정확도 업데이트 함수 추가 (Firebase용)
    const updateQAConfidenceInFirestore = async (qaId, conversationIndex, confidenceData) => {
        try {
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const updatedConversations = [...(qaItem.conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        confidence: confidenceData.confidence !== undefined ? confidenceData.confidence : updatedConversations[conversationIndex].confidence,
                        localConfidence: confidenceData.localConfidence !== undefined ? confidenceData.localConfidence : updatedConversations[conversationIndex].localConfidence,
                        globalConfidence: confidenceData.globalConfidence !== undefined ? confidenceData.globalConfidence : updatedConversations[conversationIndex].globalConfidence,
                    };
                    
                    const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                    const updateData = {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    await updateDoc(docRef, cleanDataForFirestore(updateData));
                    
                    console.log("Firestore 정확도 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("Firestore 정확도 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 6. 통합 정확도 업데이트 함수
    const updateQAConfidence = async (qaId, conversationIndex, confidenceData, updateFirestore = false) => {
        // localStorage는 항상 업데이트
        updateQAConfidenceInLocalStorage(qaId, conversationIndex, confidenceData);
        
        // Firebase는 필요시에만 업데이트
        if (updateFirestore) {
            await updateQAConfidenceInFirestore(qaId, conversationIndex, confidenceData);
        }
    };

    // 7. 관련 질문 업데이트 함수 추가 (localStorage용)
    const updateQARelatedQuestionsInLocalStorage = (qaId, conversationIndex, relatedQuestions) => {
        try {
            const currentHistory = loadFromLocalStorage();
            const qaIndex = currentHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex !== -1) {
                const updatedHistory = [...currentHistory];
                const updatedConversations = [...(updatedHistory[qaIndex].conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        relatedQuestions: relatedQuestions || [],
                        relatedQuestionsVisible: relatedQuestions && relatedQuestions.length > 0
                    };
                    
                    updatedHistory[qaIndex] = {
                        ...updatedHistory[qaIndex],
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    
                    saveToLocalStorage(updatedHistory);
                    setQaHistory(updatedHistory);
                    
                    console.log("localStorage 관련 질문 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("localStorage 관련 질문 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 8. 관련 질문 업데이트 함수 추가 (Firebase용)
    const updateQARelatedQuestionsInFirestore = async (qaId, conversationIndex, relatedQuestions) => {
        try {
            const qaItem = qaHistory.find(qa => qa.id === qaId);
            
            if (qaItem && qaItem.firestoreId) {
                const updatedConversations = [...(qaItem.conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        relatedQuestions: relatedQuestions || [],
                        relatedQuestionsVisible: relatedQuestions && relatedQuestions.length > 0
                    };
                    
                    const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                    const updateData = {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    await updateDoc(docRef, cleanDataForFirestore(updateData));
                    
                    console.log("Firestore 관련 질문 업데이트 완료:", qaId);
                }
            }
        } catch (err) {
            console.error("Firestore 관련 질문 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 9. 통합 관련 질문 업데이트 함수
    const updateQARelatedQuestions = async (qaId, conversationIndex, relatedQuestions, updateFirestore = false) => {
        // localStorage는 항상 업데이트
        updateQARelatedQuestionsInLocalStorage(qaId, conversationIndex, relatedQuestions);
        
        // Firebase는 필요시에만 업데이트
        if (updateFirestore) {
            await updateQARelatedQuestionsInFirestore(qaId, conversationIndex, relatedQuestions);
        }
    };

    // 10. 만족도 업데이트 함수 추가 (localStorage용)
    const updateQASatisfactionInLocalStorage = (qaId, conversationIndex, satisfaction) => {
        try {
            const currentHistory = loadFromLocalStorage();
            const qaIndex = currentHistory.findIndex(qa => qa.id === qaId);
            
            if (qaIndex !== -1) {
                const updatedHistory = [...currentHistory];
                const updatedConversations = [...(updatedHistory[qaIndex].conversations || [])];
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        satisfaction: satisfaction || 3 // 기본값 3
                    };
                    
                    updatedHistory[qaIndex] = {
                        ...updatedHistory[qaIndex],
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    
                    saveToLocalStorage(updatedHistory);
                    setQaHistory(updatedHistory);
                    
                    console.log("localStorage 만족도 업데이트 완료:", qaId, "만족도:", satisfaction);
                }
            }
        } catch (err) {
            console.error("localStorage 만족도 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 11. 만족도 업데이트 함수 추가 (Firebase용)
    const updateQASatisfactionInFirestore = async (qaId, conversationIndex, satisfaction) => {
        try {
            // 먼저 메모리에서 찾기
            let qaItem = qaHistory.find(qa => qa.id === qaId);
            console.log("메모리에서 찾은 qaItem:", qaItem);
            
            // 메모리에 없으면 localStorage에서 찾기
            if (!qaItem) {
                const localHistory = loadFromLocalStorage();
                qaItem = localHistory.find(qa => qa.id === qaId);
                console.log("localStorage에서 찾은 qaItem:", qaItem);
                
                // localStorage에서 찾았으면 메모리도 업데이트
                if (qaItem) {
                    setQaHistory(localHistory);
                }
            }
            
            console.log("Firebase 업데이트 시작:", qaId, conversationIndex, satisfaction);
            console.log("최종 qaItem:", qaItem);
            console.log("qaItem.firestoreId:", qaItem?.firestoreId);
            
            if (qaItem && qaItem.firestoreId) {
                const updatedConversations = [...(qaItem.conversations || [])];
                console.log("업데이트 전 conversations:", updatedConversations);
                
                if (updatedConversations[conversationIndex]) {
                    updatedConversations[conversationIndex] = {
                        ...updatedConversations[conversationIndex],
                        satisfaction: satisfaction
                    };
                    
                    console.log("업데이트 후 conversations:", updatedConversations);
                    
                    const docRef = doc(db, 'qaHistory', qaItem.firestoreId);
                    const updateData = {
                        conversations: updatedConversations,
                        updatedAt: new Date().toISOString()
                    };
                    await updateDoc(docRef, cleanDataForFirestore(updateData));
                    
                    console.log("Firestore 만족도 업데이트 완료:", qaId, "만족도:", satisfaction);
                } else {
                    console.error("conversationIndex가 범위를 벗어남:", conversationIndex, updatedConversations.length);
                }
            } else {
                console.error("qaItem 또는 firestoreId가 없음:", qaItem);
                // 다시 Firebase에 새로 저장하지 않도록 수정
                throw new Error(`QA 항목을 찾을 수 없거나 firestoreId가 없습니다: ${qaId}`);
            }
        } catch (err) {
            console.error("Firestore 만족도 업데이트 실패:", err);
            setError(err.message);
            throw err;
        }
    };

    // 12. 통합 만족도 업데이트 함수
    const updateQASatisfaction = async (qaId, conversationIndex, satisfaction, updateFirestore = false) => {
        try {
            // localStorage는 항상 업데이트
            updateQASatisfactionInLocalStorage(qaId, conversationIndex, satisfaction);
            
            // Firebase는 필요시에만 업데이트
            if (updateFirestore) {
                await updateQASatisfactionInFirestore(qaId, conversationIndex, satisfaction);
            }
        } catch (error) {
            console.error("만족도 업데이트 실패:", error);
            // Firebase 업데이트가 실패해도 localStorage는 업데이트된 상태 유지
        }
    };

    // 컨텍스트 값 설정
    const contextValue = {
        qaHistory,
        loading,
        error,
        addQA, // (newQA, saveToFirestore = false)
        deleteQA, // (qaId, deleteFromFirestore = false)
        updateQAHeadlines, // (qaId, conversationIndex, headlines, updateFirestore = false)
        updateSelectedHeadline, // (qaId, conversationIndex, headline, updateFirestore = false)
        updateQASources, // (qaId, conversationIndex, sources, updateFirestore = false)
        updateQAConfidence, // (qaId, conversationIndex, confidenceData, updateFirestore = false)
        updateQARelatedQuestions, // (qaId, conversationIndex, relatedQuestions, updateFirestore = false)
        updateQASatisfaction, // (qaId, conversationIndex, satisfaction, updateFirestore = false) - 새로 추가
        getQAHistoryByPageId, // (pageId, fromFirestore = false)
        loadAllFromFirestore, // 관리자 페이지용
        // localStorage 전용 함수들
        addQAToLocalStorage,
        deleteQAFromLocalStorage,
        updateQAConfidenceInLocalStorage,
        updateQARelatedQuestionsInLocalStorage,
        updateQASatisfactionInLocalStorage, // 새로 추가
        // Firebase 전용 함수들 (관리자 페이지용)
        addQAToFirestore,
        deleteQAFromFirestore,
        updateQAConfidenceInFirestore,
        updateQARelatedQuestionsInFirestore,
        updateQASatisfactionInFirestore, // 새로 추가
        loadFromLocalStorage,
        saveToLocalStorage
    };

    return (
        <QAHistoryContext.Provider value={contextValue}>
            {children}
        </QAHistoryContext.Provider>
    );
}

// QA 히스토리 컨텍스트 사용 훅 - 페이지별 데이터 로드 지원
export function useQAHistoryContext(pageId = null, useFirestore = false) {
    const context = useContext(QAHistoryContext);
    
    if (!context) {
        throw new Error('useQAHistoryContext must be used within a QAHistoryProvider');
    }

    const [pageQAHistory, setPageQAHistory] = useState([]);
    const [pageLoading, setPageLoading] = useState(true);
    const [pageError, setPageError] = useState(null);

    // 페이지별 QA 히스토리 로드
    useEffect(() => {
        if (!pageId) {
            setPageQAHistory([]);
            setPageLoading(false);
            return;
        }

        const loadPageQAHistory = async () => {
            try {
                setPageLoading(true);
                setPageError(null);

                const pageQAs = await context.getQAHistoryByPageId(pageId, useFirestore);
                setPageQAHistory(pageQAs);

                // Firebase를 사용하는 경우 실시간 리스너 설정
                if (useFirestore) {
                    const qaHistoryRef = collection(db, 'qaHistory');
                    const q = query(
                        qaHistoryRef, 
                        where('pageId', '==', pageId),
                        orderBy('timestamp', 'desc')
                    );
                    
                    const unsubscribe = onSnapshot(q, 
                        (snapshot) => {
                            const qaList = [];
                            snapshot.forEach((doc) => {
                                qaList.push({
                                    id: doc.id,
                                    firestoreId: doc.id,
                                    ...doc.data()
                                });
                            });
                            setPageQAHistory(qaList);
                        },
                        (err) => {
                            console.error("Firestore 실시간 QA 히스토리 로드 실패:", err);
                            setPageError(err.message);
                        }
                    );

                    return unsubscribe;
                }
            } catch (err) {
                console.error("페이지별 QA 히스토리 로드 실패:", err);
                setPageError(err.message);
            } finally {
                setPageLoading(false);
            }
        };

        loadPageQAHistory();
    }, [pageId, useFirestore, context]);

    // 페이지별 QA 히스토리가 있으면 해당 데이터 반환, 없으면 전체 데이터 반환
    return {
        ...context,
        qaHistory: pageId ? pageQAHistory : context.qaHistory,
        loading: pageId ? pageLoading : context.loading,
        error: pageId ? pageError : context.error
    };
}