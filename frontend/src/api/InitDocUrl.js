const BASE_URL = 'http://localhost:5000/flask';
export const initDocUrl = async (pageId) => {
  try {
    const response = await fetch(`${BASE_URL}/init_doc_url/${pageId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();

    if (data.success) {
      return { success: true, message: data.message };
    } else {
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error("init_doc_url API 오류:", error);
    return { success: false, error: error.message };
  }
};