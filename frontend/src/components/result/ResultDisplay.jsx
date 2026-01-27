import React, { useState } from 'react';
import ReactMarkdown from "react-markdown";
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

export default function ResultDisplay({ result, references = [], label = "답변", isFirst = true }) {
    const [copied, setCopied] = useState(false);

    if (!result) return null;

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(result);
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
                    isFirst ? 'bg-gray-100 text-gray-700' : 'bg-blue-100 text-blue-700'
                }`}>
                    {label}
                </span>
                <h2 className="text-xl font-semibold text-gray-800">
                    출력 결과
                </h2>
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
