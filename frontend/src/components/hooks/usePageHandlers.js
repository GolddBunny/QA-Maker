// src/hooks/usePageHandlers.js
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPages, savePages } from '../../utils/storage';

const BASE_URL = 'http://localhost:5000';

export function usePageHandlers(pages, updatePages, setCurrentPageId) {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const handleAddPage = async (name = `QA 시스템 ${pages.length + 1}`, sysname = '') => {
    const newPageId = Date.now().toString();

    setIsLoading(true);

    try {
      const response = await fetch(`${BASE_URL}/init/${newPageId}`, { method: 'POST' });
      const data = await response.json();

      if (data.success) {
        const newPage = {
          id: newPageId,
          name,
          sysname,
          type: 'normal',
          createdAt: new Date().toISOString()
        };

        const updatedPages = [...pages, newPage];
        updatePages(updatedPages);
        localStorage.setItem('pages', JSON.stringify(updatedPages));
        localStorage.setItem('currentPageId', newPageId);
        setCurrentPageId(newPageId);
        navigate(`/admin/${newPageId}`);
      } else {
        alert('페이지 초기화에 실패했습니다.');
      }
    } catch (err) {
      console.error('페이지 생성 오류:', err);
      alert('오류 발생');
    } finally {
      setIsLoading(false);
    }
  };

  return { handleAddPage, isLoading };
}