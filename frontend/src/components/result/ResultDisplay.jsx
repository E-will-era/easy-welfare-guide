import React from 'react';

/**
 * 문단별 중심주제 결과 표시 컴포넌트
 * @param {Object} props
 * @param {Array} props.paragraphs - 문단별 데이터 배열 [{ topic: string, content: string }]
 */
export default function ResultDisplay({ paragraphs }) {
    if (!paragraphs || paragraphs.length === 0) return null;

    // 동그라미 숫자 변환
    const circleNumbers = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩'];

    return (
        <div className="space-y-4">
            {paragraphs.map((paragraph, index) => (
                <div
                    key={index}
                    className="bg-white rounded-lg shadow-md border-2 border-blue-400 overflow-hidden"
                >
                    {/* 헤더 - 중심 내용 */}
                    <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border-b border-blue-200">
                        <span className="text-blue-500 font-bold text-lg">
                            {circleNumbers[index] || index + 1}
                        </span>
                        <span className="text-blue-600 font-bold">중심 내용_</span>
                        <span className="text-gray-800 font-semibold">
                            {paragraph.topic}
                        </span>
                    </div>
                    {/* 본문 내용 */}
                    <div className="px-4 py-3">
                        <p className="text-gray-700 text-sm leading-relaxed">
                            {paragraph.content}
                        </p>
                    </div>
                </div>
            ))}
        </div>
    );
}
