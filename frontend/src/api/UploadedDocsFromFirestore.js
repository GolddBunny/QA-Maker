
import { collection, query, where, getDocs } from "firebase/firestore";
import { db } from "../firebase/sdk";

export const loadUploadedDocsFromFirestore = async (pageId) => {
  try {
    const q = query(collection(db, "document_files"), where("page_id", "==", pageId));
    const snapshot = await getDocs(q);

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