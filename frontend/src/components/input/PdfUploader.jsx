import React from 'react';
import UploadFileIcon from '@mui/icons-material/UploadFile';

export default function PdfUploader({ file, onFileChange }) {
    return (
        <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
                PDF 파일 업로드
            </label>
            <div className="upload-box">
                <input
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={onFileChange}
                    className="hidden"
                    id="pdf-upload"
                />
                <label
                    htmlFor="pdf-upload"
                    className="cursor-pointer flex flex-col items-center"
                >
                    <UploadFileIcon className="text-gray-400 mb-2" size={48} />
                    <span className="text-gray-600 font-medium">
                        {file ? file.name : 'PDF 파일을 선택하세요'}
                    </span>
                    <span className="text-gray-400 text-sm mt-1">
                        {file ? `${(file.size / 1024).toFixed(2)} KB` : 'PDF 파일만 업로드 가능'}
                    </span>
                </label>
            </div>
        </div>
    );
}
