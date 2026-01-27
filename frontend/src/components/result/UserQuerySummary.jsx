import React, { useState, useEffect } from 'react';
import TextSnippetIcon from '@mui/icons-material/TextSnippet';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import CloseIcon from '@mui/icons-material/Close';
import DownloadIcon from '@mui/icons-material/Download';

export default function UserQuerySummary({ type, text, file }) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [objectUrl, setObjectUrl] = useState(null);
    const [showImageModal, setShowImageModal] = useState(false);

    // 파일(이미지/PDF)이 변경되면 Object URL 생성 및 정리
    useEffect(() => {
        if (file) {
            const url = URL.createObjectURL(file);
            setObjectUrl(url);

            // Cleanup function to revoke URL
            return () => {
                URL.revokeObjectURL(url);
            };
        }
        return () => {
            setObjectUrl(null);
        };
    }, [file]);

    if (!type) return null;

    return (
        <>
            <div className="info-box mb-6">
                <h2 className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide flex justify-between items-center">
                    <span>질문 내용</span>
                    <span className="text-xs font-normal text-gray-400">
                        {type === 'text' && (isExpanded ? '접기' : '더 보기')}
                        {type === 'image' && '클릭하여 확대'}
                        {type === 'pdf' && '클릭하여 다운로드'}
                    </span>
                </h2>

                <div className="flex items-start">
                    <div className="mr-3 mt-1 text-blue-600">
                        {type === 'text' && <TextSnippetIcon />}
                        {type === 'pdf' && <PictureAsPdfIcon />}
                        {type === 'image' && <CameraAltIcon />}
                    </div>

                    <div className="flex-1 overflow-hidden">
                        {/* 텍스트 타입: 클릭 시 확장/축소 */}
                        {type === 'text' && (
                            <div
                                onClick={() => setIsExpanded(!isExpanded)}
                                className={`text-gray-800 text-sm leading-relaxed cursor-pointer hover:bg-gray-100 p-1 rounded transition-colors ${!isExpanded ? 'line-clamp-2' : ''}`}
                            >
                                {text || '내용 없음'}
                            </div>
                        )}

                        {/* PDF 타입: 클릭 시 다운로드 */}
                        {type === 'pdf' && file && (
                            <a
                                href={objectUrl}
                                download={file.name}
                                className="group block cursor-pointer hover:bg-gray-100 p-1 rounded transition-colors"
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-gray-800 font-medium truncate max-w-[200px] sm:max-w-xs">
                                            {file.name}
                                        </p>
                                        <p className="text-xs text-gray-500 mt-1">
                                            {(file.size / 1024).toFixed(2)} KB
                                        </p>
                                    </div>
                                    <DownloadIcon className="text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" size={20} />
                                </div>
                            </a>
                        )}

                        {/* 이미지 타입: 클릭 시 모달 확대 */}
                        {type === 'image' && file && objectUrl && (
                            <div
                                onClick={() => setShowImageModal(true)}
                                className="group cursor-pointer hover:bg-gray-100 p-1 rounded transition-colors inline-block"
                            >
                                <div className="relative rounded-lg overflow-hidden border border-gray-200 w-24 h-24 bg-gray-100">
                                    <img
                                        src={objectUrl}
                                        alt="Uploaded preview"
                                        className="w-full h-full object-cover"
                                    />
                                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all flex items-center justify-center">
                                        <span className="text-white opacity-0 group-hover:opacity-100 text-xs font-bold bg-black bg-opacity-50 px-2 py-1 rounded">확대</span>
                                    </div>
                                </div>
                                <div className="mt-2 text-xs text-gray-500">
                                    {(file.size / 1024).toFixed(2)} KB
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* 이미지 확대 모달 */}
            {showImageModal && objectUrl && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-90 p-4" onClick={() => setShowImageModal(false)}>
                    <div className="relative max-w-full max-h-full">
                        <button
                            onClick={() => setShowImageModal(false)}
                            className="absolute -top-10 right-0 text-white hover:text-gray-300 transition-colors"
                        >
                            <CloseIcon size={32} />
                        </button>
                        <img
                            src={objectUrl}
                            alt="Full preview"
                            className="max-w-full max-h-[85vh] object-contain rounded shadow-2xl"
                            onClick={(e) => e.stopPropagation()} // 이미지 클릭 시 모달 닫기 방지
                        />
                    </div>
                </div>
            )}
        </>
    );
}
