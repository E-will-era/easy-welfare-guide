import React from 'react';

export default function TextInput({ value, onChange }) {
    return (
        <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
                텍스트 입력
            </label>
            <textarea
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder="여기에 텍스트를 입력하세요..."
                className="text-input-area"
            />
        </div>
    );
}
