import { db } from '../firebase/sdk';
import { 
  collection, 
  doc, 
  getDocs, 
  getDoc,
  setDoc, 
  updateDoc, 
  deleteDoc,
  query,
  where,
  orderBy
} from "firebase/firestore";

// 페이지 목록 가져오기
export const getPages = async () => {
  try {
    const querySnapshot = await getDocs(collection(db, "pages"));
    const pages = querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
    return pages;
  } catch (error) {
    console.error('페이지 목록 가져오기 실패:', error);
    return [];
  }
};

// 페이지 목록 저장하기
export const savePages = async (pages) => {
  try {
    const promises = pages.map(page => 
      setDoc(doc(db, "pages", page.id), page)
    );
    await Promise.all(promises);
    return true;
  } catch (error) {
    console.error('페이지 목록 저장 실패:', error);
    return false;
  }
};

// 현재 페이지 ID 가져오기
let currentPageId = null;
export const getCurrentPageId = () => {
  return currentPageId;
};

// 현재 페이지 ID 설정하기
export const setCurrentPageId = (pageId) => {
  currentPageId = pageId;
};

// 페이지 문서 목록 가져오기
export const getPageDocuments = async (pageId) => {
  try {
    const docRef = doc(db, "pageDocuments", pageId);
    const docSnap = await getDoc(docRef);
    
    if (docSnap.exists()) {
      return docSnap.data().documents || [];
    } else {
      return [];
    }
  } catch (error) {
    console.error('페이지 문서 목록 가져오기 실패:', error);
    return [];
  }
};

// 페이지 문서 목록 저장하기
export const savePageDocuments = async (pageId, documents) => {
  try {
    const docRef = doc(db, "pageDocuments", pageId);
    await setDoc(docRef, { 
      documents,
      updatedAt: new Date().toISOString()
    });
    return true;
  } catch (error) {
    console.error('페이지 문서 목록 저장 실패:', error);
    return false;
  }
};

// 메인 타입 페이지 찾기
export const findMainPage = async () => {
  try {
    const q = query(
      collection(db, "pages"), 
      where("type", "==", "main")
    );
    const querySnapshot = await getDocs(q);
    
    if (!querySnapshot.empty) {
      const doc = querySnapshot.docs[0];
      return { id: doc.id, ...doc.data() };
    }
    return null;
  } catch (error) {
    console.error('메인 페이지 찾기 실패:', error);
    return null;
  }
};

// 새 페이지 생성하기
export const createPage = async (name, type = 'normal') => {
  try {
    const newPageId = Date.now().toString();
    const newPage = {
      id: newPageId,
      name,
      type,
      createdAt: new Date().toISOString()
    };
    
    // 만약 type이 'main'이고 다른 'main' 타입 페이지가 있다면
    // 기존 main 타입 페이지를 normal로 변경
    if (type === 'main') {
      const pages = await getPages();
      const mainPage = pages.find(page => page.type === 'main');
      
      if (mainPage) {
        await updateDoc(doc(db, "pages", mainPage.id), {
          type: 'normal'
        });
      }
    }
    
    // 새 페이지 저장
    await setDoc(doc(db, "pages", newPageId), newPage);
    return newPage;
  } catch (error) {
    console.error('페이지 생성 실패:', error);
    return null;
  }
};

// 페이지 타입 변경하기
export const changePageType = async (pageId, newType) => {
  try {
    // 타입을 'main'으로 변경하는 경우, 기존 main 타입 페이지를 normal로 변경
    if (newType === 'main') {
      const pages = await getPages();
      const mainPage = pages.find(page => page.type === 'main');
      
      if (mainPage && mainPage.id !== pageId) {
        await updateDoc(doc(db, "pages", mainPage.id), {
          type: 'normal'
        });
      }
    }
    
    // 해당 페이지 타입 변경
    await updateDoc(doc(db, "pages", pageId), {
      type: newType
    });
    
    return true;
  } catch (error) {
    console.error('페이지 타입 변경 실패:', error);
    return false;
  }
};

// 특정 페이지 가져오기
export const getPage = async (pageId) => {
  try {
    const docRef = doc(db, "pages", pageId);
    const docSnap = await getDoc(docRef);
    
    if (docSnap.exists()) {
      return { id: docSnap.id, ...docSnap.data() };
    }
    return null;
  } catch (error) {
    console.error('페이지 가져오기 실패:', error);
    return null;
  }
};

// 페이지 저장하기
export const savePage = async (page) => {
  try {
    // 페이지를 'main' 타입으로 변경하는 경우
    if (page.type === 'main') {
      const pages = await getPages();
      const mainPage = pages.find(p => p.id !== page.id && p.type === 'main');
      
      if (mainPage) {
        await updateDoc(doc(db, "pages", mainPage.id), {
          type: 'normal'
        });
      }
    }
    
    // 페이지 저장
    await setDoc(doc(db, "pages", page.id), page);
    return true;
  } catch (error) {
    console.error('페이지 저장 실패:', error);
    return false;
  }

// export const savePage = (page) => {
//   let pages = getPages();
//   const index = pages.findIndex(p => p.id === page.id);

//   if (page.type === 'main') {
//     // 모든 페이지의 type을 'normal'로 초기화
//     pages = pages.map(p => ({
//       ...p,
//       type: p.id === page.id ? 'main' : 'normal'
//     }));
//   } else {
//     // 그냥 업데이트만
//     if (index >= 0) {
//       pages[index] = page;
//     } else {
//       pages.push(page);
//     }
//   }

//   return savePages(pages);
};

// 페이지 삭제하기
export const removePage = async (pageId) => {
  try {
    // 삭제할 페이지 정보 가져오기
    const pageToRemove = await getPage(pageId);
    
    // 현재 페이지가 삭제되는 경우 현재 페이지 ID 삭제
    if (getCurrentPageId() === pageId) {
      setCurrentPageId(null);
    }
    
    // main 타입 페이지가 삭제되는 경우, 다른 페이지를 main으로 설정
    if (pageToRemove && pageToRemove.type === 'main') {
      const pages = await getPages();
      const remainingPages = pages.filter(page => page.id !== pageId);
      
      if (remainingPages.length > 0) {
        // 첫 번째 페이지를 main으로 설정
        await updateDoc(doc(db, "pages", remainingPages[0].id), {
          type: 'main'
        });
      }
    }
    
    // 페이지 삭제
    await deleteDoc(doc(db, "pages", pageId));
    
    // 페이지 문서도 함께 삭제
    try {
      await deleteDoc(doc(db, "pageDocuments", pageId));
    } catch (docError) {
      // 문서가 없어도 무시
      console.log('페이지 문서 삭제 (문서 없음):', pageId);
    }
    
    return true;
  } catch (error) {
    console.error('페이지 삭제 실패:', error);
    return false;
  }
};

// 페이지 이름 업데이트 (PageContext와 일관성 유지)
export const updatePageName = async (pageId, newName) => {
  try {
    const pageRef = doc(db, "pages", pageId);
    await updateDoc(pageRef, {
      name: newName
    });
    
    return {
      success: true,
      updatedPage: { id: pageId, name: newName }
    };
  } catch (error) {
    console.error('페이지 이름 업데이트 오류:', error);
    return { success: false, error: error.message };
  }
};

// 페이지 시스템 이름 업데이트 (PageContext와 일관성 유지)
export const updatePageSysName = async (pageId, newSysName) => {
  try {
    const pageRef = doc(db, "pages", pageId);
    await updateDoc(pageRef, {
      sysname: newSysName
    });
    
    return {
      success: true,
      updatedPage: { id: pageId, sysname: newSysName }
    };
  } catch (error) {
    console.error('페이지 시스템 이름 업데이트 오류:', error);
    return { success: false, error: error.message };
  }
};
