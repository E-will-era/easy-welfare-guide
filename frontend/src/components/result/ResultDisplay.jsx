import React from 'react';
import ReactMarkdown from "react-markdown";

export default function ResultDisplay({ result, references = [], label = "답변", isFirst = true }) {
    if (!result) return null;

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
        </div>
    );
}
