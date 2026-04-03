import React from 'react';
import LinearProgress from '@mui/material/LinearProgress';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import animationSprite from '../../assets/images/animation.png';
import apiErrorImage from '../../assets/images/apiError.png';

const PHASE_MESSAGES = {
    analyze_difficulty: '문서의 복잡도를 분석하고 있어요...',
    re_translate: '다시 쉬운 말로 바꾸고 있어요...',
    validate: '내용을 검증하고 있어요...',
    completed: '분석이 완료되었어요!',
};

const PHASE_PROGRESS = {
    analyze_difficulty: 25,
    re_translate: 50,
    validate: 75,
    completed: 100,
};

export default function SecondLoadingSpinner({ phase}) {
    const isError = phase === 'close' || phase === 'failed' || phase === 'error';
    const message = isError
        ? '오류가 발생했습니다.'
        : (phase ? PHASE_MESSAGES[phase] : '2차 분석 준비 중...');
    const progress = phase ? (PHASE_PROGRESS[phase] || 10) : 10;

    // 에러 상태일 때 에러 UI 표시
    if (isError) {
        return (
        <Paper
            elevation={0}
            sx={{
                borderRadius: '16px',
                p: 3,
                bgcolor: 'rgba(255,255,255,0.9)',
                border: '2px solid #bfdbfe',
            }}
        >
            <div className="flex flex-col items-center justify-center py-12">
                <img
                    src={apiErrorImage}
                    alt="API Error"
                    className="w-40 h-40 mb-4 object-contain"
                />
                <p className="text-gray-600 font-medium text-center px-4">{"에러가 발생했습니다."}</p>
            </div>
        </Paper>
        );
    }


    return (
        <Paper
            elevation={0}
            sx={{
                borderRadius: '16px',
                p: 3,
                bgcolor: 'rgba(255,255,255,0.9)',
                border: '2px solid #bfdbfe',
            }}
            className="animate-fade-in-up"
        >
            <div className="flex flex-col items-center justify-center py-6">
                {/* LinearProgress 로딩 바 */}
                <Box sx={{ width: '80%', mb: 2 }}>
                    <LinearProgress
                        variant="determinate"
                        value={progress}
                        sx={{
                            height: 6,
                            borderRadius: 3,
                            backgroundColor: '#e0e0e0',
                            '& .MuiLinearProgress-bar': {
                                borderRadius: 3,
                                backgroundColor: '#3b82f6',
                            },
                        }}
                    />
                </Box>

                {/* 스프라이트 애니메이션 (작은 사이즈) */}
                <div
                    className="w-24 h-24 mb-3"
                    style={{
                        backgroundImage: `url(${animationSprite})`,
                        backgroundSize: '300% 300%',
                        animation: 'sprite-animation-second 1.2s steps(1) infinite',
                    }}
                />
                <p className="text-gray-600 font-medium text-sm">{message}</p>

                <style>{`
                    @keyframes sprite-animation-second {
                        0%    { background-position: 0% 0%; }
                        11.1% { background-position: 50% 0%; }
                        22.2% { background-position: 100% 0%; }
                        33.3% { background-position: 0% 50%; }
                        44.4% { background-position: 50% 50%; }
                        55.5% { background-position: 100% 50%; }
                        66.6% { background-position: 0% 100%; }
                        77.7% { background-position: 50% 100%; }
                        88.8% { background-position: 100% 100%; }
                        100%  { background-position: 0% 0%; }
                    }
                `}</style>
            </div>
        </Paper>
    );
}
