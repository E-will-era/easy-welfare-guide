import React from 'react';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import UploadFileIcon from '@mui/icons-material/UploadFile';

export default function ImageUploader({ file, onFileChange }) {
    return (
        <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
                이미지 촬영 또는 업로드
            </label>
            <div className="grid grid-cols-2 md:grid-cols-1 gap-4">
                {/* 카메라 촬영 (모바일 전용) */}
                <div className="upload-box md:hidden">
                    <input
                        type="file"
                        accept="image/*"
                        capture="environment"
                        onChange={onFileChange}
                        className="hidden"
                        id="camera-capture"
                    />
                    <label
                        htmlFor="camera-capture"
                        className="w-full h-full cursor-pointer flex flex-col items-center justify-center"
                    >
                        <CameraAltIcon className="text-gray-400 mb-2" size={40} />
                        <span className="text-gray-600 font-medium text-sm">
                            카메라 촬영
                        </span>
                    </label>
                </div>

                {/* 파일 선택 */}
                <div className="upload-box">
                    <input
                        type="file"
                        accept="image/*"
                        onChange={onFileChange}
                        className="hidden"
                        id="image-upload"
                    />
                    <label
                        htmlFor="image-upload"
                        className="w-full h-full cursor-pointer flex flex-col items-center justify-center"
                    >
                        <UploadFileIcon className="text-gray-400 mb-2" size={40} />
                        <span className="text-gray-600 font-medium text-sm">
                            파일 선택
                        </span>
                    </label>
                </div>
            </div>

            {file && (
                <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-sm text-gray-700">
                        <span className="font-medium">선택된 파일:</span> {file.name}
                    </p>
                    <p className="text-sm text-gray-500">
                        {(file.size / 1024).toFixed(2)} KB
                    </p>
                </div>
            )}
        </div>
    );
}
