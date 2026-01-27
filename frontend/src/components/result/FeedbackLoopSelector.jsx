import React from 'react';
import SentimentSatisfiedAltIcon from '@mui/icons-material/SentimentSatisfiedAlt';
import SentimentVeryDissatisfiedIcon from '@mui/icons-material/SentimentVeryDissatisfied';

/**
 * 피드백 선택 컴포넌트
 * @param {function} onYes - "네" 클릭 시 호출 (만족 → references 표시)
 * @param {function} onNo - "아니오" 클릭 시 호출 (불만족 → 재질의)
 */
export default function FeedbackLoopSelector({ onYes, onNo }) {
    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center gap-2 mb-4">
                <h2 className="text-xl font-semibold text-gray-800">
                    답변이 도움이 되셨나요?
                </h2>
            </div>
            <div className="flex gap-3">
                <button
                    onClick={onYes}
                    className="mode-button mode-button-inactive flex-1 flex items-center justify-center gap-2"
                >
                    <SentimentSatisfiedAltIcon fontSize="small" />
                    네, 충분해요
                </button>
                <button
                    onClick={onNo}
                    className="mode-button mode-button-inactive flex-1 flex items-center justify-center gap-2"
                >
                    <SentimentVeryDissatisfiedIcon fontSize="small" />
                    아니오, 더 알려주세요
                </button>
            </div>
        </div>
    );
}
