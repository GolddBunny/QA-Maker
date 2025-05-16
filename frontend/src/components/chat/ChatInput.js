import React from 'react';

const ChatInput = ({ newQuestion, setNewQuestion, handleSendQuestion, handleSearch,handleUrlOptionClick, handleDocumentOptionClick }) => {
    return (
        <div className="search-container-chat">
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
            <button class="icon-btn" onClick={handleSearch}>
            <svg class="icon" viewBox="0 0 24 24">
                <circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="2" fill="none"/>
                <line x1="14.5" y1="14.5" x2="20" y2="20" stroke="currentColor" stroke-width="2"/>
            </svg>
            </button>

            <div class="bottom-left-buttons">
            <button class="url-btn" onClick={handleUrlOptionClick}>URL 추가하기</button>
            <button class="doc-btn" onClick={handleDocumentOptionClick}>문서 추가하기</button>
            </div>
        </div>
    );
};

export default ChatInput;