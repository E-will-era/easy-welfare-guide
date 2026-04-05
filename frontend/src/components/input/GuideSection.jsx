import React from 'react';
import ChecklistIcon from '@mui/icons-material/Checklist';

export default function GuideSection() {
    return (
        <div className="guide-box">
            <div className="flex items-start">
                <ChecklistIcon className="text-blue-500 mr-3 mt-1" size={24} />
                <div>
                    <h2 className="text-lg font-semibold text-blue-900 mb-2">
                        사용 안내
                    </h2>
                    <ul className="text-blue-800 space-y-1 text-sm">
                        <li>• 텍스트 입력, 이미지 촬영/업로드 중 하나를 선택하세요</li>
                        <li>• 이미지는 png, jpg, jpeg 파일만 업로드 가능합니다</li>
                        <li>• 이미지는 카메라로 촬영하거나 파일을 선택할 수 있습니다</li>
                        <li>• 입력 완료 후 '제출하기' 버튼을 클릭하세요</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}
