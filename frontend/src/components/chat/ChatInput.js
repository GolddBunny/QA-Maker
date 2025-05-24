import React from 'react';

const ChatInput = ({
  newQuestion,
  setNewQuestion,
  handleSendQuestion,
  handleUrlOptionClick,
  handleDocumentOptionClick,
  addedUrls,
  setAddedUrls,
  selectedFile,
  setSelectedFile,
  showUrlInput,
  setShowUrlInput,
  urlInput,
  setUrlInput,
  handleAddUrl
}) => {
    return (
        <div className="search-container-chat">
            <div className="attachment-container">
                {/* URL 입력 박스 - 가장 먼저 표시 */}
                {showUrlInput && (
                <div className="url-input-box-chat">
                    <input
                    type="text"
                    placeholder="URL을 입력하세요"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    className="url-input-main"
                    />
                    <button 
                    onClick={() => {
                        handleAddUrl();
                        setShowUrlInput(false); // 입력 후 닫기
                    }} 
                    className="add-url-btn"
                    >
                    추가
                    </button>
                </div>
                )}

                {/* URL 리스트 */}
                {addedUrls.length > 0 && (
                <div className="url-list">
                    {addedUrls.map((url, index) => (
                    <div key={index} className="selected-file-container">
                        <div className="selected-file">
                        <span className="url-icon">🌐</span>
                        <span>{url}</span>
                        <button 
                            className="file-cancel"
                            onClick={() => {
                            const newUrls = [...addedUrls];
                            newUrls.splice(index, 1);
                            setAddedUrls(newUrls);
                            }}
                            title="URL 제거"
                        >
                            ×
                        </button>
                        </div>
                    </div>
                    ))}
                </div>
                )}

                {/* 선택된 파일 미리보기 */}
                {selectedFile && (
                <div className="selected-file-container">
                    <div className="selected-file">
                    <img src="/assets/document.png" alt="파일" className="file-icon" />
                    <span className="file-name">{selectedFile.name}</span>
                    <button 
                        className="file-cancel" 
                        onClick={() => setSelectedFile(null)}
                        title="파일 선택 취소"
                    >
                        ×
                    </button>
                    </div>
                </div>
                )}
            </div>
            <textarea 
                id="search-input-chat"
                placeholder="질문을 입력하세요..."
                value={newQuestion}
                onChange={(e) => setNewQuestion(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendQuestion();
                    }
                }}
            />
            <button className="icon-btn" onClick={handleSendQuestion}>
            <svg className="icon" viewBox="0 0 24 24">
                <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="2" fill="none"/>
                <line x1="14.5" y1="14.5" x2="20" y2="20" stroke="currentColor" strokeWidth="2"/>
            </svg>
            </button>

            <div className="bottom-left-buttons">
            <button className="url-btn" onClick={handleUrlOptionClick}>URL 추가하기</button>
            <button className="doc-btn" onClick={handleDocumentOptionClick}>문서 추가하기</button>
            </div>
        </div>
    );
};

export default ChatInput;