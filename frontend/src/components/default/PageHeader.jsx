import React from 'react';
import mainLogo from '../../assets/images/main_logo.png';

export default function PageHeader() {
    return (
        <div className="mb-6 text-center">
            <img
                src={mainLogo}
                alt="이음:새 로고"
                className="w-72 sm:w-96 mx-auto"
            />
        </div>
    );
}
