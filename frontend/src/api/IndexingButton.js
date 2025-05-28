import { startUrlCrawling, crawlAndStructure, line1 } from './UrlApi';
import { processDocuments } from './DocumentApi';

const BASE_URL = 'http://localhost:5000';
const UPDATE_URL = `${BASE_URL}/update`;
const APPLY_URL = `${BASE_URL}/apply`;

// 전체 플로우 실행 
// URL 크롤링 → 웹 구조화(웹 크롤링 + 1줄만들기) → 문서 구조화(DocumentApi.py-processDocuments) → 문서 인덱싱(generate_routes.py-apply) -> 웹 증분 인덱싱(generate_routes.py-update)
export const executeFullPipeline = async (pageId) => {
  try {
    console.log("🚀 QA System Build 파이프라인 시작:", pageId);
    
    // 1단계: URL 크롤링
    console.log("1️⃣ URL 크롤링 시작...");
    const crawlingResult = await startUrlCrawling(pageId);
    
    if (!crawlingResult.success) {
      throw new Error(`URL 크롤링 실패: ${crawlingResult.error}`);
    }
    
    console.log("✅ URL 크롤링 완료:", crawlingResult.results);
    
    // 2단계-1: 웹 크롤링 및 구조화 (crawling_and_structuring.py)
    console.log("2️⃣-1 웹 크롤링 및 구조화 시작...");
    const structuringResult = await crawlAndStructure(pageId);
    
    if (!structuringResult.success) {
      throw new Error(`웹 크롤링 및 구조화 실패: ${structuringResult.error}`);
    }
    
    console.log("✅ 웹 크롤링 및 구조화 완료:", structuringResult.results);
    
    // 2단계-2: 텍스트 정리 (line1.py)
    console.log("2️⃣-2 웹 크롤링 텍스트 line1 정리 시작...");
    const line1Result = await line1(pageId);
    
    if (!line1Result.success) {
      throw new Error(`웹 크롤링 텍스트 line1 정리 실패: ${line1Result.error}`);
    }
    
    console.log("✅ 웹 크롤링 텍스트 line1 정리 완료:", line1Result.results);

    // 3단계: 문서 구조화
    console.log("3️⃣ 문서 구조화 시작...");
    const documentResult = await processDocuments(pageId);
    
    if (!documentResult.success) {
      throw new Error(`문서 구조화 실패: ${documentResult.error}`);
    }

    console.log("✅ 문서 구조화 완료:", documentResult.results);

    // 4단계: 최종 인덱싱
    console.log("4️⃣ 문서 인덱싱 시작...");
    const indexingResult = await applyIndexing(pageId);
    
    if (!indexingResult.success) {
      throw new Error(`인덱싱 실패: ${indexingResult.error}`);
    }
    
    console.log("✅ 문서 인덱싱 완료!");

    // 5단계: 웹 증분 인덱싱
    console.log("5️⃣ 웹 증분 인덱싱 시작...");
    const updateResult = await updateIndexing(pageId);
    
    if (!updateResult.success) {
      throw new Error(`웹 증분 인덱싱 실패: ${updateResult.error}`);
    }

    console.log("✅ 웹 증분 인덱싱 완료!");
    
    return {
      success: true,
      results: {
        crawling: crawlingResult.results,
        structuring: structuringResult.results,
        line1: line1Result.results,
        document: documentResult.results,
        indexing: indexingResult,
        update: updateResult.results
      }
    };
    
  } catch (error) {
    console.error("❌ 파이프라인 실행 중 오류:", error);
    return { success: false, error: error.message };
  }
};

// 인덱싱 시작
export const applyIndexing = async (pageId) => {
  try {
    const response = await fetch(`${APPLY_URL}/${pageId}`, {
      method: 'POST',
    });
    const data = await response.json();

    return data.success
      ? { success: true }
      : { success: false, error: data.error };
  } catch (err) {
    console.error("applyIndexing 에러:", err);
    return { success: false, error: err.message };
  }
};

// 증분 인덱싱 시작
export const updateIndexing = async (pageId) => {
  try {
    const response = await fetch(`${UPDATE_URL}/${pageId}`, {
      method: 'POST',
    });
    const data = await response.json();

    return data.success
      ? { success: true }
      : { success: false, error: data.error };
  } catch (error) {
    console.error("updateIndexing 에러:", error);
    return { success: false, error: error.message };
  }
};