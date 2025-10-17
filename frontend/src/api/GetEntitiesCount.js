import { fetchEntities } from "../api/AllParquetView";

// 특정 페이지에서 엔티티 총 개수를 가져오는 함수
export const GetEntitiesCount = async (pageId, entitySearchTerm = "") => {
    try {
        if (!pageId) {
            console.warn("pageId가 제공되지 않음");
            return { success: false, totalCount: 0, error: "pageId가 제공되지 않음" };
        }

        // 엔티티 데이터 API에서 불러오기
        const entities = await fetchEntities(pageId);

        if (!Array.isArray(entities)) {
            console.warn("불러온 엔티티 데이터가 배열이 아님");
            return { success: false, totalCount: 0, error: "엔티티 데이터가 배열이 아님" };
        }

        // 검색어가 있을 때만 필터링, 없으면 전체 개수 반환
        let filtered = entities;
        
        if (entitySearchTerm && entitySearchTerm.trim() !== "") {
            filtered = entities.filter(item => {
                const hasTitle = item.title && typeof item.title === 'string';
                const matchesSearch = hasTitle
                    ? item.title.toLowerCase().includes(entitySearchTerm.toLowerCase())
                    : false;
                return hasTitle && matchesSearch;
            });
        } else {
            // 검색어가 없을 때는 title이 있는 모든 엔티티 카운트
            filtered = entities.filter(item => {
                return item.title && typeof item.title === 'string';
            });
        }

        // 엔티티 개수 반환
        return { 
            success: true, 
            totalCount: filtered.length,
            error: null 
        };

    } catch (error) {
        console.error("엔티티 개수 조회 실패:", error);
        return { 
            success: false, 
            totalCount: 0, 
            error: error.message || "엔티티 개수 조회 중 오류가 발생했습니다." 
        };
    }
};