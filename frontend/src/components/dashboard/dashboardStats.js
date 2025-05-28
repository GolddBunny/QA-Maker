export const getDateStats = (uploadedUrls, uploadedDocs) => {
    const dateMap = {};

    uploadedUrls.forEach(item => {
        if (item.date) {
            const date = item.date.substring(0, 10);
            if (!dateMap[date]) {
                dateMap[date] = { url: 0, doc: 0 };
            }
            dateMap[date].url++;
        }
    });

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

    for (let i = 10; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = d.toISOString().substring(0, 10);
        const shortDate = dateStr.substring(8);

        dates.push({
            date: shortDate,
            fullDate: dateStr,
            url: dateMap[dateStr]?.url || 0,
            doc: dateMap[dateStr]?.doc || 0,
        });
    }

    return dates;
};

export const getKnowledgeGraphDateStats = (knowledgeGraphStats) => {
    const dateMap = {};

    knowledgeGraphStats.forEach(item => {
        if (item.date) {
            const date = item.date.substring(0, 10);
            if (!dateMap[date]) {
                dateMap[date] = { entity: 0, relationship: 0 };
            }
            if (item.process_type === 'entity') {
                dateMap[date].entity++;
            } else if (item.process_type === 'relationship') {
                dateMap[date].relationship++;
            }
        }
    });

    const today = new Date();
    const dates = [];

    for (let i = 10; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = d.toISOString().substring(0, 10);
        const shortDate = dateStr.substring(8);

        dates.push({
            date: shortDate,
            fullDate: dateStr,
            entity: dateMap[dateStr]?.entity || 0,
            relationship: dateMap[dateStr]?.relationship || 0,
        });
    }

    return dates;
};

export const getGraphBuildDateStats = (graphBuildStats) => {
    const dateMap = {};

    graphBuildStats.forEach(item => {
        if (item.date && item.entity_count && item.relationship_count) {
            const date = item.date.substring(0, 10);
            if (!dateMap[date]) {
                dateMap[date] = { entity: 0, relationship: 0 };
            }
            dateMap[date].entity += item.entity_count;
            dateMap[date].relationship += item.relationship_count;
        }
    });

    const today = new Date();
    const dates = [];

    for (let i = 10; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const dateStr = d.toISOString().substring(0, 10);
        const shortDate = dateStr.substring(8);

        dates.push({
            date: shortDate,
            fullDate: dateStr,
            entity: dateMap[dateStr]?.entity || 0,
            relationship: dateMap[dateStr]?.relationship || 0,
        });
    }

    return dates;
};