import React from 'react';

export default function LoadingSpinner() {
    return (
        <div className="flex flex-col items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-600 font-medium">분석 중입니다...</p>
        </div>
    );
}
