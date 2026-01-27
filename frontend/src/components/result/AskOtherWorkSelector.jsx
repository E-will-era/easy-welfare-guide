import React from 'react';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import LaunchIcon from '@mui/icons-material/Launch';

/**
 * 피드백 선택 컴포넌트
 * @param {function} onRetry- 새로운 질문 실행
 * @param {function} onOtherWork - 보건복지상담 홈페이지로 이동
 */
export default function AskOtherWorkSelector({ onRetry, onOtherWork }) {
    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex gap-3">
                <button
                    onClick={onRetry}
                    className="mode-button mode-button-inactive flex-1 flex items-center justify-center gap-2"
                >
                    <RestartAltIcon fontSize="small" />
                    다시 질문하기
                </button>
                <button
                    onClick={onOtherWork}
                    className="mode-button mode-button-inactive flex-1 flex items-center justify-center gap-2"
                >
                    <LaunchIcon fontSize="small" />
                    보건복지상담센터
                </button>
            </div>
        </div>
    );
}
