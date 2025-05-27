const BASE_URL = 'http://localhost:5000';

export const fetchEntities = async (id, setError) => {
  if (!id) return null;

  try {
    const res = await fetch(`${BASE_URL}/api/entity/${id}`);
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(`Entity fetch error: ${res.statusText}, Details: ${JSON.stringify(errorData)}`);
    }
    const data = await res.json();
    return data;
  } catch (err) {
    console.error("entity fetch error:", err);
    if (setError) setError("엔티티 데이터 로드 실패");
    return [];
  }
};

export const fetchRelationships = async (id, setError) => {
  if (!id) return null;

  try {
    const res = await fetch(`${BASE_URL}/api/relationship/${id}`);
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(`Relationship fetch error: ${res.statusText}, Details: ${JSON.stringify(errorData)}`);
    }
    const data = await res.json();
    return data;
  } catch (err) {
    console.error("relationship fetch error:", err);
    if (setError) setError("관계 데이터 로드 실패");
    return [];
  }
};