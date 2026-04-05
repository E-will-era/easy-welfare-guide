import React, { useState } from 'react';
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

function getReliability(refCount) {
    if (refCount >= 3) return { label: '신뢰도 높음', color: 'bg-green-100 text-green-700 border-green-300' };
    if (refCount === 2) return { label: '신뢰도 중간', color: 'bg-yellow-100 text-yellow-700 border-yellow-300' };
    return { label: '신뢰도 낮음', color: 'bg-red-100 text-red-700 border-red-300' };
}

export default function ResultDisplay({ result, references = [], label = "답변", isFirst = true }) {
    const [copied, setCopied] = useState(false);
    const [showDisclaimer, setShowDisclaimer] = useState(false);

    if (!result) return null;

    const reliability = getReliability(references.length);

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
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 text-xs font-medium rounded ${
                        isFirst ? 'bg-blue-500 text-white' : 'bg-blue-100 text-blue-700'
                    }`}>
                        {label}
                    </span>
                    <span className={`px-2 py-1 text-xs font-medium rounded border ${reliability.color}`}>
                        {reliability.label}
                    </span>
                </div>
                <span className="text-xs text-gray-500">
                    참조 문서 {references.length}건
                </span>
            </div>
            <div
                className="bg-blue-50 rounded-lg p-4 border border-blue-200 cursor-pointer select-none mb-3"
                onClick={() => setShowDisclaimer(!showDisclaimer)}
            >
                <div className="flex items-center justify-between text-blue-700">
                    <span>
                        {references.length >= 3
                            ? 'AI 요약본입니다. 정확한 내용은 원문과 링크를 확인하세요.'
                            : '관련 공식 문서가 충분하지 않습니다. 원문 공고를 직접 확인해 주세요.'
                        }
                    </span>
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
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 prose prose-sm prose-slate max-w-none
                            prose-headings:text-slate-800 prose-headings:font-bold prose-headings:mt-4 prose-headings:mb-2
                            prose-p:text-slate-700 prose-p:leading-relaxed prose-p:my-1.5
                            prose-strong:text-slate-900 prose-strong:font-semibold
                            prose-ul:my-2 prose-ul:pl-5 prose-ol:my-2 prose-ol:pl-5
                            prose-li:my-0.5 prose-li:text-slate-700
                            prose-table:border-collapse prose-th:bg-slate-100 prose-th:border prose-th:border-slate-300 prose-th:px-3 prose-th:py-1.5 prose-th:text-left
                            prose-td:border prose-td:border-slate-200 prose-td:px-3 prose-td:py-1.5
                            prose-blockquote:border-l-4 prose-blockquote:border-blue-300 prose-blockquote:bg-blue-50 prose-blockquote:pl-4 prose-blockquote:py-2 prose-blockquote:italic
                            prose-hr:my-4 prose-hr:border-slate-200">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
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
