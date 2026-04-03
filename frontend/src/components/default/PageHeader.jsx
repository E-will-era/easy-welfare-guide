import React from 'react';
import mainLogo from '../../assets/images/main_logo.png';

export default function PageHeader() {
    return (
        <div className="mb-6 text-center">
            <img
                src={mainLogo}
                alt="이음:새 로고"
                className="w-32 sm:w-48 mx-auto"
            />
            <h3 className="font-bold text-gray-500">
                정보를 가까이, 이해를 이어드립니다
            </h3>
        </div>
    );
}
