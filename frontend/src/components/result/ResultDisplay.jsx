import React, { useState } from 'react';
import ReactMarkdown from "react-markdown";
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

export default function ResultDisplay({ result, references = [], label = "답변", isFirst = true }) {
    const [copied, setCopied] = useState(false);
    const [showDisclaimer, setShowDisclaimer] = useState(false);

    if (!result) return null;

    const handleCopy = async () => {
        try {
            const textToCopy = `*AI 요약본입니다. 실제 내용과 차이가 있을 수 있습니다*\n\n${result}`;
            await navigator.clipboard.writeText(textToCopy);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('복사 실패:', err);
        }
    };

    return (
        <div className={`bg-white rounded-lg shadow-md p-6 ${!isFirst ? 'border-l-4 border-blue-500' : ''}`}>
            <div className="flex items-center gap-2 mb-4">
                <span className={`px-2 py-1 text-xs font-medium rounded ${
                    isFirst ? 'bg-blue-500 text-white' : 'bg-blue-100 text-blue-700'
                }`}>
                    {label}
                </span>
                <h2 className="text-xl font-semibold text-gray-800">
                    {
                        isFirst ? '내용을 정리했어요!' : '내용을 더 쉽게 정리했어요!'
                    }
                </h2>
            </div>
            <div
                className="bg-blue-50 rounded-lg p-4 border border-blue-200 cursor-pointer select-none mb-3"
                onClick={() => setShowDisclaimer(!showDisclaimer)}
            >
                <div className="flex items-center justify-between text-blue-700">
                    <span>AI 요약본입니다. 정확한 내용은 원문 공고에서 확인하세요.</span>
                    <span className={`transform transition-transform ${showDisclaimer ? 'rotate-180' : ''}`}>
                        ▼
                    </span>
                </div>
                {showDisclaimer && (
                    <ul className="mt-3 pt-3 border-t border-blue-200 text-sm text-blue-600 space-y-1">
                        <li>• AI 요약 결과는 법적 효력이 없습니다.</li>
                        <li>• 실제 내용과 차이가 있을 수 있습니다.</li>
                        <li>• 신청 전 반드시 원문 공고를 확인하세요.</li>
                        <li>• 정확한 정보는 해당 기관에 문의하세요.</li>
                        <li>• 본 서비스 사용으로 발생하는 불이익에 대해 책임을 지지 않습니다.</li>
                    </ul>
                )}
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <ReactMarkdown>
                    {result}
                </ReactMarkdown>
            </div>
            <button
                onClick={handleCopy}
                className={`w-full py-2 rounded-lg font-medium mt-3 transition-colors flex items-center justify-center gap-2 text-sm ${
                    copied
                        ? 'bg-gray-400 text-white cursor-default'
                        : 'bg-[#1C8BE7] text-white hover:bg-[#1a7ed4]'
                }`}
                disabled={copied}
            >
                <ContentCopyIcon sx={{ fontSize: 16 }} />
                {copied ? '복사 완료' : '복사'}
            </button>
        </div>
    );
}
