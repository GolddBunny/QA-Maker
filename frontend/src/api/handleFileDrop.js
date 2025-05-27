import { useState } from 'react';

const BASE_URL = 'http://localhost:5000';
const UPLOAD_URL = `${BASE_URL}/upload-documents`;

export const FileDropHandler = ({
  uploadedDocs,
  setUploadedDocs,
  setDuplicateFileName,
  setIsFileLoading,
  setHasDocuments,
  isAnyProcessing,
  pageId
}) => {
  const allowedFileTypes = [
    'application/pdf',
    'text/plain',
    'application/octet-stream', //hwp
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
    'application/msword' // .doc
  ];

  const handleFileDrop = async (e) => {
    e.preventDefault();

    if (isAnyProcessing) return;
    setIsFileLoading(true);

    try {
      const files = Array.from(e.dataTransfer ? e.dataTransfer.files : e.target.files);

      const filteredFiles = files.filter(file => {
        const isAllowedType = allowedFileTypes.includes(file.type);
        const isHwpFile = file.name.toLowerCase().endsWith('.hwp');
        return isAllowedType || isHwpFile;
      });

      if (filteredFiles.length === 0) {
        alert(".pdf, .hwp, .docx, .txt 파일만 업로드할 수 있습니다.");
        return;
      }

      const existingDocs = uploadedDocs
        .map(doc => (doc.original_filename ? doc.original_filename.toLowerCase() : ''))
        .filter(name => name);
      const newFiles = filteredFiles.filter(file => !existingDocs.includes(file.name.toLowerCase()));

      if (newFiles.length === 0) {
        setDuplicateFileName(filteredFiles[0].name);
        return;
      }

      const formData = new FormData();
      newFiles.forEach(file => formData.append('files', file));

      const response = await fetch(`${UPLOAD_URL}/${pageId}`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      if (!data.success) {
        alert('파일 업로드에 실패했습니다.');
        return;
      }

      const newDocObjs = data.uploaded_files; // ← 서버에서 보낸 firebase 저장 결과

      const updated = [...uploadedDocs, ...newDocObjs];
      setUploadedDocs(updated);
      //localStorage.setItem(`uploadedDocs_${currentPageId}`, JSON.stringify(updated));
      setHasDocuments(true);

    } catch (error) {
      console.error('파일 업로드 오류:', error);
      alert('파일 업로드 중 오류가 발생했습니다.');
    } finally {
      setIsFileLoading(false);
    }
  };

  return { handleFileDrop };
};