
import { collection, query, where, getDocs } from "firebase/firestore";
import { db } from "../firebase/sdk";

// Firestore에서 특정 페이지에 업로드된 문서 목록을 불러오는 함수
export const loadUploadedDocsFromFirestore = async (pageId) => {
  try {
    // "document_files" 컬렉션에서 page_id가 일치하는 문서만 조회
    const q = query(collection(db, "document_files"), where("page_id", "==", pageId));

    // 쿼리 실행 후 스냅샷 반환
    const snapshot = await getDocs(q);

    // 스냅샷에서 실제 문서 데이터만 추출
    const docs = snapshot.docs.map(doc => doc.data());
    return {
      docs,
      count: docs.length,
    };
    
  } catch (error) {
    console.error("Firestore 문서 목록 조회 실패:", error);
    return { docs: [], count: 0 };
  }
};