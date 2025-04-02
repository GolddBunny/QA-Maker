import React from 'react';

const ChatInput = ({ newQuestion, setNewQuestion, handleSendQuestion, isLoading }) => {
    return (
        <div className="input-container">
            <textarea 
                className="input-box" 
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
            <button 
                className="send-button" 
                onClick={handleSendQuestion}
                disabled={!newQuestion.trim() || isLoading} 
                type="button"
            >
                전송
            </button>
        </div>
    );
};

export default ChatInput; 