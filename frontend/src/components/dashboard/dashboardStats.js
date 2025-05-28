// 랜덤 값 생성 헬퍼 함수
const getRandomValue = (min = 1, max = 10) => {
    return Math.floor(Math.random() * (max - min + 1)) + min;
};

// 업로드된 URL 및 문서 데이터를 기반으로 날짜별 통계를 반환하는 함수
export const getDateStats = (uploadedUrls, uploadedDocs) => {
    const dateMap = {};

    // URL 업로드 데이터 처리
    uploadedUrls.forEach(item => {
        if (item.date) {
            const date = item.date.substring(0, 10); // 날짜(yyyy-mm-dd) 추출
            if (!dateMap[date]) {
                dateMap[date] = { url: 0, doc: 0 };
            }
            dateMap[date].url++;
        }
    });

    // 문서 업로드 데이터 처리
    uploadedDocs.forEach(doc => {
        if (doc.date) {
            const date = doc.date.substring(0, 10);
            if (!dateMap[date]) {
                dateMap[date] = { url: 0, doc: 0 };
            }
            dateMap[date].doc++;
        }
    });

    const today = new Date();
    const dates = [];

    // 최근 11일간의 날짜별 데이터 생성
    for (let i = 10; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = d.toISOString().substring(0, 10); // 전체 날짜 문자열
        const shortDate = dateStr.substring(8); // 일자만 추출 (예: "28")

        // 실제 데이터가 있으면 사용, 없으면 랜덤 값 생성
        const urlCount = dateMap[dateStr]?.url || getRandomValue(0, 8);
        const docCount = dateMap[dateStr]?.doc || getRandomValue(0, 6);

        dates.push({
            date: shortDate, // 시각화용 짧은 날짜
            fullDate: dateStr, // 전체 날짜 (yyyy-mm-dd)
            url: urlCount,
            doc: docCount,
        });
    }

    return dates;
};

// 지식 그래프 구축 중 entity/relationship 프로세스 수를 날짜별로 집계하는 함수
export const getKnowledgeGraphDateStats = (knowledgeGraphStats) => {
    const dateMap = {};

    // 프로세스 항목 순회
    knowledgeGraphStats.forEach(item => {
        if (item.date) {
            const date = item.date.substring(0, 10);
            if (!dateMap[date]) {
                dateMap[date] = { entity: 0, relationship: 0 };
            }
            // process_type에 따라 카운트 증가
            if (item.process_type === 'entity') {
                dateMap[date].entity++;
            } else if (item.process_type === 'relationship') {
                dateMap[date].relationship++;
            }
        }
    });

    const today = new Date();
    const dates = [];

    // 최근 11일간 날짜별 entity/relationship 수치 생성
    for (let i = 10; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = d.toISOString().substring(0, 10);
        const shortDate = dateStr.substring(8);

        // 실제 데이터가 있으면 사용, 없으면 랜덤 값 생성
        const entityCount = dateMap[dateStr]?.entity || getRandomValue(5, 25);
        const relationshipCount = dateMap[dateStr]?.relationship || getRandomValue(3, 15);

        dates.push({
            date: shortDate,
            fullDate: dateStr,
            entity: entityCount,
            relationship: relationshipCount,
        });
    }

    return dates;
};

// 지식 그래프 빌드 결과의 날짜별 entity 및 relationship 개수를 집계하는 함수
export const getGraphBuildDateStats = (graphBuildStats) => {
    const dateMap = {};

    // 그래프 빌드 항목 순회
    graphBuildStats.forEach(item => {
        if (item.date && item.entity_count && item.relationship_count) {
            const date = item.date.substring(0, 10);
            if (!dateMap[date]) {
                dateMap[date] = { entity: 0, relationship: 0 };
            }
            // 해당 날짜에 entity 및 relationship 수 누적
            dateMap[date].entity += item.entity_count;
            dateMap[date].relationship += item.relationship_count;
        }
    });

    const today = new Date();
    const dates = [];

    // 최근 11일간 날짜별 누적 entity 및 relationship 수치 생성
    for (let i = 10; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = d.toISOString().substring(0, 10);
        const shortDate = dateStr.substring(8);

        // 실제 데이터가 있으면 사용, 없으면 랜덤 값 생성
        const entityCount = dateMap[dateStr]?.entity || getRandomValue(50, 200);
        const relationshipCount = dateMap[dateStr]?.relationship || getRandomValue(30, 150);

        dates.push({
            date: shortDate,
            fullDate: dateStr,
            entity: entityCount,
            relationship: relationshipCount,
        });
    }

    return dates;
};