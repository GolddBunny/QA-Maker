import { getStorage, ref, listAll, getMetadata } from 'firebase/storage';
import BASE_URL from "../../config/url";  

export const fetchKnowledgeGraphStats = async (pageId, setKnowledgeGraphStats) => {
    try {
        console.log('지식그래프 통계 로드 시작:', pageId);
        
        const storage = getStorage();
        const resultsRef = ref(storage, `pages/${pageId}/results/`);
        const listResult = await listAll(resultsRef);
        console.log('파일 목록:', listResult.items.map(item => item.name));
        
        const statsData = [];
        
        for (const itemRef of listResult.items) {
            try {
                const metadata = await getMetadata(itemRef);
                const customMetadata = metadata.customMetadata || {};
                
                if (customMetadata.process_type === 'index' || itemRef.name.includes('entities') || itemRef.name.includes('relationships')) {
                    const filename = itemRef.name;
                    
                    let process_type;
                    if (filename.includes('entities')) {
                        process_type = 'entity';
                    } else if (filename.includes('relationships')) {
                        process_type = 'relationship';
                    } else {
                        continue;
                    }
                    
                    let date = customMetadata.date || 
                            customMetadata.created_date || 
                            customMetadata.upload_date ||
                            metadata.timeCreated;
                    
                    if (date) {
                        try {
                            date = new Date(date).toISOString();
                        } catch (error) {
                            console.warn(`날짜 변환 실패 ${filename}:`, error);
                            continue;
                        }
                    } else {
                        console.warn(`날짜 정보 없음 ${filename}`);
                        continue;
                    }
                    
                    const statsItem = {
                        date: date,
                        process_type: process_type,
                        execution_time: customMetadata.execution_time || '0',
                        filename: filename
                    };
                    
                    statsData.push(statsItem);
                }
            } catch (error) {
                console.warn(`파일 ${itemRef.name} 메타데이터 처리 중 오류:`, error);
                continue;
            }
        }
        
        statsData.sort((a, b) => new Date(b.date) - new Date(a.date));
        console.log('최종 지식그래프 통계:', statsData);
        setKnowledgeGraphStats(statsData);
        
    } catch (error) {
        console.error('지식그래프 통계 로드 중 오류:', error);
        setKnowledgeGraphStats([]);
    }
};