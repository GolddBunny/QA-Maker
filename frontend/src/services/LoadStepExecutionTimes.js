import { doc, getDoc } from "firebase/firestore";
import { db } from "../firebase/sdk";

// 특정 pageId에 해당하는 Firestore 문서에서 stepExecutionTimes 데이터를 로드
export const loadStepExecutionTimes = async (pageId) => {
    try {
        console.log("stepExecutionTimes 로딩 시작:", pageId);
        
        // dashboard 컬렉션에서 pageId로 된 문서 참조
        const docRef = doc(db, 'dashboard', pageId);
        const docSnap = await getDoc(docRef);
        
        // 문서가 존재하는 경우
        if (docSnap.exists()) {
            const data = docSnap.data();
            console.log("Firestore에서 가져온 전체 데이터:", data);
            
            // Firestore에 저장된 stepExecutionTimes 필드 추출
            // (없으면 빈 객체로 초기화)
            const stepTimesRaw = data.stepExecutionTimes || {}; 

            // 필요한 단계별 실행 시간만 추출
            // 없는 값은 null로 처리
            const stepTimes = {
                crawling: stepTimesRaw.crawling || null,
                document: stepTimesRaw.document || null,
                indexing: stepTimesRaw.indexing || null,
                structuring: stepTimesRaw.structuring || null,
            };
            
            console.log("stepExecutionTimes 로딩 완료:", stepTimes);
            return stepTimes;
        } else {
            console.warn("문서가 존재하지 않습니다:", pageId);
            return {
                crawling: null,
                document: null,
                indexing: null,
                structuring: null,
            };
        }
    } catch (error) {
        console.error("stepExecutionTimes 로딩 중 오류:", error);
        // 오류 발생 시 기본값 반환
        return {
            crawling: null,
            document: null,
            indexing: null,
            structuring: null,
        };
    }
};