const BASE_URL = 'http://localhost:5000';
const UPDATE_URL = `${BASE_URL}/update`;
const APPLY_URL = `${BASE_URL}/apply`;

export const applyIndexing = async (pageId) => {
  try {
    const response = await fetch(`${APPLY_URL}/${pageId}`, {
      method: 'POST',
    });
    const data = await response.json();

    return data.success
      ? { success: true, execution_time: data.execution_time }
      : { success: false, error: data.error };
  } catch (err) {
    console.error("applyIndexing 에러:", err);
    return { success: false, error: err.message };
  }
};

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