import React from 'react';

export default function GhostButton({
    onClick,
    label,
    Icon,
    isActive = false,
    isLight = false,
    className = ''
}) {
    const darkStyles = isActive
        ? 'bg-white/20 text-white border-white shadow-[0_0_15px_rgba(255,255,255,0.4)] scale-[1.02]'
        : 'bg-transparent text-white/40 border-transparent hover:border-white/20 hover:text-white/80';

    const lightStyles = isActive
        ? 'bg-gray-100 text-gray-800 border-gray-400 shadow-sm scale-[1.02]'
        : 'bg-transparent text-gray-500 border-gray-300 hover:bg-gray-50 hover:text-gray-900 hover:border-gray-400';

    return (
        <button
            onClick={onClick}
            className={`flex items-center justify-center gap-2 py-2 px-4 text-xs font-bold transition-all duration-300 border-2 rounded-lg
            ${isLight ? lightStyles : darkStyles}
            ${className}`}
        >
            {Icon && <Icon sx={{ fontSize: 16 }} />}
            {label}
        </button>
    );
}