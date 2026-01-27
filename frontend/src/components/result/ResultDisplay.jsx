import React from 'react';

export default function ResultDisplay({ result }) {
    if (!result) return null;

    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
                출력 결과
            </h2>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <pre className="text-gray-700 whitespace-pre-wrap font-mono text-sm">
                    {result}
                </pre>
            </div>
        </div>
    );
}
