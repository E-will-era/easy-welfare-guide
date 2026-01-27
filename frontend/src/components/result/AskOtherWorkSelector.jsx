import React from 'react';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import LaunchIcon from '@mui/icons-material/Launch';

/**
 * 피드백 선택 컴포넌트
 * @param {function} onYes - "네" 클릭 시 호출 (만족 → references 표시)
 * @param {function} onNo - "아니오" 클릭 시 호출 (불만족 → 재질의)
 */
export default function AskOtherWorkSelector({ onYes, onNo }) {
    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex gap-3">
                <button
                    onClick={onYes}
                    className="mode-button mode-button-inactive flex-1 flex items-center justify-center gap-2"
                >
                    <RestartAltIcon fontSize="small" />
                    다시 질문하기
                </button>
                <button
                    onClick={onNo}
                    className="mode-button mode-button-inactive flex-1 flex items-center justify-center gap-2"
                >
                    <LaunchIcon fontSize="small" />
                    보건복지상담 홈페이지
                </button>
            </div>
        </div>
    );
}
