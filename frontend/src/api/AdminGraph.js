const BASE_URL = 'http://localhost:5000/flask';

// 그래프 데이터를 가져오는 함수
export const fetchGraphData = async ({
  pageId,
  graphDataCacheRef,
  setGraphData
}) => {
  if (!pageId) return;

  const cacheKey = `graphData-${pageId}`;

  // 캐시에 이미 데이터가 있으면 캐시에서 불러오기
  if (graphDataCacheRef.current[cacheKey]) {
    console.log("그래프 데이터 캐시에서 로드됨");
    const cachedData = graphDataCacheRef.current[cacheKey];

    setGraphData(prev => {
      // 이전 상태와 다르면 업데이트
      if (JSON.stringify(prev) !== JSON.stringify(cachedData)) {
        return cachedData;
      }
      return prev;
    });
    return; // 캐시 사용했으면 함수 종료
  }

  // 로컬 JSON 파일에서 그래프 데이터 불러오기
  const loadGraphFromLocalJson = async () => {
    const filePath = `/json/${pageId}/admin_graphml_data.json`;
    try {
      const res = await fetch(filePath, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        console.log("로컬 JSON 파일에서 그래프 데이터 로드됨");
        return data;
      } else {
        console.log("로컬 JSON 파일 없음 또는 로딩 실패");
        return null;
      }
    } catch (err) {
      console.error("로컬 JSON 로딩 중 오류:", err);
      return null;
    }
  };

  // 서버에 그래프 생성 요청 보내기
  const generateGraphViaServer = async () => {
    console.log("서버로 그래프 생성 요청 전송 중...");
    const res = await fetch(`${BASE_URL}/admin/all-graph`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',  // 캐시 방지
      },
      body: JSON.stringify({ page_id: pageId }),  // 페이지 ID 전달
    });
    console.log("서버 응답 상태:", res.status);
    if (!res.ok) throw new Error(`서버 그래프 생성 실패: ${res.status}`);

    return await res.json();  // 서버에서 JSON 데이터 반환
  };

  try {
    // 먼저 로컬 JSON에서 시도
    let data = await loadGraphFromLocalJson();
    if (!data) {
      // 로컬에 없으면 서버에서 생성
      data = await generateGraphViaServer();
    }

    // 데이터가 있으면 캐시에 저장하고 상태 업데이트
    if (data) {
      graphDataCacheRef.current[cacheKey] = data;
      setGraphData(data);
    }
  } catch (err) {
    console.error("그래프 데이터 로드 중 오류:", err);
  }
};