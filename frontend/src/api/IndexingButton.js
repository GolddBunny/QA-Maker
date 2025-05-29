import { startUrlCrawling, crawlAndStructure, line1, documentDownloader } from './UrlApi';
import { processDocuments } from './DocumentApi';

const BASE_URL = 'http://localhost:5000';
const UPDATE_URL = `${BASE_URL}/flask/update`;
const APPLY_URL = `${BASE_URL}/flask/apply`;

// 전체 플로우 실행 
// URL 크롤링 → 웹 구조화(웹 크롤링 + 1줄만들기) → 문서 구조화(DocumentApi.py-processDocuments) → 문서 인덱싱(generate_routes.py-apply) -> 웹 증분 인덱싱(generate_routes.py-update)
export const executeFullPipeline = async (pageId, onStepComplete) => {
  try {
    console.log("🚀 QA System Build 파이프라인 시작:", pageId);

    const executionTimes = {
      crawling: null,
      structuring: null,
      document: null,
      indexing: null,
      total: null
    };
    const pipelineStartTime = Date.now();

    // 1단계: URL 크롤링
    console.log("1️⃣ URL 크롤링 시작...");
    const crawlStart = Date.now();
    const crawlingResult = await startUrlCrawling(pageId);
    const crawlEnd = Date.now();
    executionTimes.crawling = (crawlEnd - crawlStart) / 1000;

    if (!crawlingResult.success) {
      if (
        crawlingResult.error &&
        crawlingResult.error.includes("크롤링할 URL이 없습니다")
      ) {
        console.log("⚠️ URL이 없으므로 웹 크롤링 생략, 문서 구조화부터 시작합니다.");
        executionTimes.crawling = 0;
        if (onStepComplete) onStepComplete('crawling', executionTimes.crawling);

        executionTimes.structuring = 0;
        if (onStepComplete) onStepComplete('structuring', executionTimes.structuring);

        // 문서 구조화
        console.log("3️⃣ 문서 구조화 시작...");
        const docStart = Date.now();
        const documentResult = await processDocuments(pageId);
        const docEnd = Date.now();
        executionTimes.document = (docEnd - docStart) / 1000;

        if (!documentResult.success) throw new Error(`문서 구조화 실패: ${documentResult.error}`);
        if (onStepComplete) onStepComplete('document', executionTimes.document);

        // 인덱싱
        console.log("4️⃣ 문서 인덱싱 시작...");
        const indexingResult = await applyIndexing(pageId);
        if (!indexingResult.success) throw new Error(`인덱싱 실패: ${indexingResult.error}`);
        console.log("✅ 문서 인덱싱 완료!");

        // 웹 증분 인덱싱
        console.log("5️⃣ 웹 증분 인덱싱 시작...");
        const updateResult = await updateIndexing(pageId);
        if (!updateResult.success) throw new Error(`웹 증분 인덱싱 실패: ${updateResult.error}`);
        console.log("✅ 웹 증분 인덱싱 완료!");

        executionTimes.indexing = (indexingResult.execution_time || 0) + (updateResult.execution_time || 0);
        if (onStepComplete) onStepComplete('indexing', executionTimes.indexing);
        executionTimes.total = (Date.now() - pipelineStartTime) / 1000;

        return {
          success: true,
          execution_times: executionTimes,
          results: {
            crawling: null,
            structuring: null,
            document: documentResult.results,
            indexing: indexingResult
          },
        };
      }
      throw new Error(`URL 크롤링 실패: ${crawlingResult.error}`);
    }

    console.log("✅ URL 크롤링 완료:", crawlingResult.results);
    if (onStepComplete) onStepComplete('crawling', executionTimes.crawling);

    // 2단계-1: 웹 구조화
    console.log("2️⃣-1 웹 크롤링 및 구조화 시작...");
    const structStart = Date.now();
    const structuringResult = await crawlAndStructure(pageId);
    if (!structuringResult.success) throw new Error(`웹 크롤링 및 구조화 실패: ${structuringResult.error}`);

    // 2단계-2: line1
    console.log("2️⃣-2 웹 크롤링 텍스트 line1 정리 시작...");
    const line1Result = await line1(pageId);
    if (!line1Result.success) throw new Error(`line1 정리 실패: ${line1Result.error}`);
    

    // 2단계-3: 문서 다운로더 (document_downloader.py)
    console.log("2️⃣-3 문서 다운로더 시작...");
    const documentDownloaderResult = await documentDownloader(pageId);
    
    if (!documentDownloaderResult.success) {
      throw new Error(`문서 다운로더 실패: ${documentDownloaderResult.error}`);
    }

    console.log("✅ 문서 다운로더 완료:", documentDownloaderResult.results);
    const structEnd = Date.now();
    executionTimes.structuring = (structEnd - structStart) / 1000;
    if (onStepComplete) onStepComplete('structuring', executionTimes.structuring);

    // 3단계: 문서 구조화
    console.log("3️⃣ 문서 구조화 시작...");
    const docStart = Date.now();
    const documentResult = await processDocuments(pageId);
    const docEnd = Date.now();
    executionTimes.document = (docEnd - docStart) / 1000;

    if (!documentResult.success) throw new Error(`문서 구조화 실패: ${documentResult.error}`);
    console.log("✅ 문서 구조화 완료:", documentResult.results);
    if (onStepComplete) onStepComplete('document', executionTimes.document);

    // 4단계: 문서 인덱싱
    console.log("4️⃣ 문서 인덱싱 시작...");
    const indexingResult = await applyIndexing(pageId);
    if (!indexingResult.success) throw new Error(`인덱싱 실패: ${indexingResult.error}`);

    // 5단계: 웹 증분 인덱싱
    console.log("5️⃣ 웹 증분 인덱싱 시작...");
    const updateResult = await updateIndexing(pageId);
    if (!updateResult.success) throw new Error(`웹 증분 인덱싱 실패: ${updateResult.error}`);
    executionTimes.indexing = (indexingResult.execution_time || 0) + (updateResult.execution_time || 0);
    if (onStepComplete) onStepComplete('indexing', executionTimes.indexing);

    console.log("✅ 전체 인덱싱 완료!");
    executionTimes.total = (Date.now() - pipelineStartTime) / 1000;

    return {
      success: true,
      execution_times: executionTimes,
      results: {
        crawling: crawlingResult.results,
        structuring: structuringResult.results,
        document: documentResult.results,
        indexing: indexingResult,
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
    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      const text = await response.text();
      console.error("❌ JSON이 아닌 응답을 받았습니다:", text.slice(0, 300));
      return { success: false, error: "서버에서 JSON이 아닌 응답을 반환했습니다." };
    }
  const data = await response.json();
    return data.success
      ? { success: true, execution_time: data.execution_time }
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
      ? { success: true , execution_time: data.execution_time || null }
      : { success: false, error: data.error };
  } catch (error) {
    console.error("updateIndexing 에러:", error);
    return { success: false, error: error.message };
  }
};