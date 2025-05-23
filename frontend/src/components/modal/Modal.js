import React from 'react';
import '../../styles/Modal.css';

const Modal = ({ isOpen, onClose, title, message, type = 'alert', onConfirm }) => {
    if (!isOpen) return null;

    const handleOverlayClick = (e) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            onClose();
        }
    };

    return (
        <div 
            className="modal-overlay" 
            onClick={handleOverlayClick}
            onKeyDown={handleKeyDown}
            tabIndex={-1}
        >
            <div className="modal-container">
                <div className="modal-header">
                    <h3 className="modal-title">{title}</h3>
                </div>
                <div className="modal-body">
                    <p className="modal-message">{message}</p>
                </div>
                <div className="modal-footer">
                    {type === 'confirm' ? (
                        <>
                            <button 
                                className="modal-btn modal-btn-cancel" 
                                onClick={onClose}
                                autoFocus
                            >
                                취소
                            </button>
                            <button 
                                className="modal-btn modal-btn-confirm" 
                                onClick={onConfirm}
                            >
                                다운로드
                            </button>
                        </>
                    ) : (
                        <button 
                            className="modal-btn modal-btn-confirm" 
                            onClick={onClose}
                            autoFocus
                        >
                            확인
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Modal;