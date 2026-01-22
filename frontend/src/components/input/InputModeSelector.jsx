import React from 'react';
import TextSnippetIcon from '@mui/icons-material/TextSnippet';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
export default function InputModeSelector({ currentMode, onModeChange }) {
    return (
        <div className="flex gap-3 mb-6">
            <button
                onClick={() => onModeChange('text')}
                className={`mode-button ${currentMode === 'text'
                    ? 'mode-button-active'
                    : 'mode-button-inactive'
                    }`}
            >
                <TextSnippetIcon size={20} />
                텍스트
            </button>
            <button
                onClick={() => onModeChange('pdf')}
                className={`mode-button ${currentMode === 'pdf'
                    ? 'mode-button-active'
                    : 'mode-button-inactive'
                    }`}
            >
                <PictureAsPdfIcon size={20} />
                PDF
            </button>
            <button
                onClick={() => onModeChange('image')}
                className={`mode-button ${currentMode === 'image'
                    ? 'mode-button-active'
                    : 'mode-button-inactive'
                    }`}
            >
                <CameraAltIcon size={20} />
                이미지
            </button>
        </div>
    );
}
