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
        </div>
    );
}
