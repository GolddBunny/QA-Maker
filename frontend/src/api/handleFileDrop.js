import { useState } from 'react';
const BASE_URL = 'http://localhost:5000/flask';
const UPLOAD_URL = `${BASE_URL}/upload-documents`;

// 파일 드롭하고 업로드 처리
export const FileDropHandler = ({
  uploadedDocs,
  setUploadedDocs,
  setDuplicateFileName,
  setIsFileLoading,
  setHasDocuments,
  isAnyProcessing,
  pageId,
  setDocCount
}) => {

  // 업로드 허용 파일 타입 정의 (.pdf, .txt, .hwp, .docx, .doc)
  const allowedFileTypes = [
    'application/pdf',
    'text/plain',
    'application/octet-stream', //hwp
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
    'application/msword' // .doc
  ];

  // 실제 파일 드롭 또는 선택 시 처리 함수
  const handleFileDrop = async (e) => {
    e.preventDefault();   // 기본 브라우저 동작 방지

    // 다른 처리 중이면 바로 종료
    if (isAnyProcessing) return;
    setIsFileLoading(true);   // 업로드 진행 상태로 설정

    try {
      // 드롭된 파일 또는 input으로 선택된 파일 가져오기
      const files = Array.from(e.dataTransfer ? e.dataTransfer.files : e.target.files);

      // 허용된 파일 타입만 필터링
      const filteredFiles = files.filter(file => {
        const isAllowedType = allowedFileTypes.includes(file.type);
        const isHwpFile = file.name.toLowerCase().endsWith('.hwp');
        return isAllowedType || isHwpFile;
      });

      // 허용 파일이 없으면 경고
      if (filteredFiles.length === 0) {
        alert(".pdf, .hwp, .docx, .txt 파일만 업로드할 수 있습니다.");
        return;
      }

      // 이미 업로드된 파일과 중복 여부 체크
      const existingDocs = uploadedDocs
        .map(doc => (doc.original_filename ? doc.original_filename.toLowerCase() : ''))
        .filter(name => name);
      const newFiles = filteredFiles.filter(file => !existingDocs.includes(file.name.toLowerCase()));

      // 중복 파일만 있을 경우 상태 업데이트 후 종료
      if (newFiles.length === 0) {
        setDuplicateFileName(filteredFiles[0].name);
        return;
      }

      // FormData 생성 후 업로드할 파일 추가
      const formData = new FormData();
      newFiles.forEach(file => formData.append('files', file));

      // 서버에 파일 업로드 요청
      const response = await fetch(`${UPLOAD_URL}/${pageId}`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      if (!data.success) {
        alert('파일 업로드에 실패');
        return;
      }

      const newDocObjs = data.uploaded_files; // 서버에서 반환한 업로드 결과

      // 기존 문서 목록에 새로 업로드한 문서 추가 후 상태 업데이트
      const updated = [...uploadedDocs, ...newDocObjs];
      setUploadedDocs(updated);
      setHasDocuments(true);  // 문서 존재 여부 true로 변경
      setDocCount(updated.length);  // 업로드 문서 개수 업데이트

    } catch (error) {
      console.error('파일 업로드 오류:', error);
      alert('파일 업로드 중 오류가 발생했습니다.');
    } finally {
      setIsFileLoading(false);  // 업로드 진행 상태 해제
    }
  };

  return { handleFileDrop };
};