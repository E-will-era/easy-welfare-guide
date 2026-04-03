import React from 'react';

export default function GhostButton({
    onClick,
    label,
    Icon,
    isActive = false,
    isLight = false,
    isFab = false,
    className = ''
}) {
    // FAB 스타일 (모바일 원형 버튼)
    if (isFab) {
        return (
            <button
                onClick={onClick}
                className={`ghost-button-fab ${className}`}
                title={label}
                aria-label={label}
            >
                {Icon && <Icon sx={{ fontSize: 24 }} />}
            </button>
        );
    }

    // 기본 스타일 (데스크탑)
    const styleClass = isLight
        ? (isActive ? 'ghost-button-light-active' : 'ghost-button-light')
        : (isActive ? 'ghost-button-dark-active' : 'ghost-button-dark');

    return (
        <button
            onClick={onClick}
            className={`ghost-button ${styleClass} ${className}`}
            title={label}
        >
            {Icon && <Icon sx={{ fontSize: 16 }} />}
            <span>{label}</span>
        </button>
    );
}