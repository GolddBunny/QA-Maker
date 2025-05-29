const BASE_URL = 'http://localhost:5000/flask';

export const fetchGraphData = async ({
  pageId,
  graphDataCacheRef,
  setGraphData
}) => {
  if (!pageId) return;

  const cacheKey = `graphData-${pageId}`;

  if (graphDataCacheRef.current[cacheKey]) {
    console.log("그래프 데이터 캐시에서 로드됨");
    const cachedData = graphDataCacheRef.current[cacheKey];
    setGraphData(prev => {
      if (JSON.stringify(prev) !== JSON.stringify(cachedData)) {
        return cachedData;
      }
      return prev;
    });
    return;
  }

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

  const generateGraphViaServer = async () => {
    console.log("서버로 그래프 생성 요청 전송 중...");
    const res = await fetch(`${BASE_URL}/admin/all-graph`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
      },
      body: JSON.stringify({ page_id: pageId }),
    });
    console.log("서버 응답 상태:", res.status);
    if (!res.ok) throw new Error(`서버 그래프 생성 실패: ${res.status}`);

    return await res.json();
  };

  try {
    let data = await loadGraphFromLocalJson();
    if (!data) {
      data = await generateGraphViaServer();
    }

    if (data) {
      graphDataCacheRef.current[cacheKey] = data;
      setGraphData(data);
    }
  } catch (err) {
    console.error("그래프 데이터 로드 중 오류:", err);
  }
};