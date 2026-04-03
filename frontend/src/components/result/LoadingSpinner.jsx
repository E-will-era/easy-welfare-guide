import React from 'react';
import LinearProgress from '@mui/material/LinearProgress';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import animationSprite from '../../assets/images/animation.png';
import apiErrorImage from '../../assets/images/apiError.png';

const PHASE_MESSAGES = {
    relevance: '복지 문서인지 확인하고 있어요...',
    search: '관련 정보를 검색하고 있어요...',
    summarize: '문서를 요약하고 있어요...',
    translate: '쉬운 말로 바꾸고 있어요...',
    validate: '내용을 검증하고 있어요...',
    completed: '분석이 완료되었어요!',
};

const PHASE_PROGRESS = {
    relevance: 15,
    search: 30,
    summarize: 50,
    translate: 70,
    validate: 90,
    completed: 100,
};

export default function LoadingSpinner({ phase, errorMessage, onRetry }) {
    const isError = phase === 'close' || phase === 'failed';
    const message = isError
        ? (errorMessage || '오류가 발생했습니다.')
        : (phase ? PHASE_MESSAGES[phase] : '분석 준비 중...');
    const progress = phase ? PHASE_PROGRESS[phase] : 10;

    // 에러 상태일 때 에러 UI 표시
    if (isError) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <img
                    src={apiErrorImage}
                    alt="API Error"
                    className="w-40 h-40 mb-4 object-contain"
                />
                <p className="text-gray-600 font-medium text-center px-4">{message}</p>
                {onRetry && (
                    <Button
                        variant="contained"
                        onClick={onRetry}
                        sx={{
                            mt: 3,
                            py: 1.5,
                            px: 4,
                            borderRadius: '12px',
                            fontWeight: 600,
                            textTransform: 'none',
                            background: 'linear-gradient(to right, #3b82f6, #0ea5e9)',
                            boxShadow: '0 4px 14px rgba(59, 130, 246, 0.3)',
                            '&:hover': {
                                boxShadow: '0 6px 20px rgba(59, 130, 246, 0.4)',
                            },
                        }}
                    >
                        다른 질문하기
                    </Button>
                )}
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center py-12">
            {/* LinearProgress 로딩 바 */}
            <Box sx={{ width: '80%', mb: 3 }}>
                <LinearProgress
                    variant="determinate"
                    value={progress}
                    sx={{
                        height: 8,
                        borderRadius: 4,
                        backgroundColor: '#e0e0e0',
                        '& .MuiLinearProgress-bar': {
                            borderRadius: 4,
                            backgroundColor: '#3b82f6',
                        },
                    }}
                />
            </Box>

            {/* 스프라이트 애니메이션 */}
            <div
                className="w-40 h-40 mb-4"
                style={{
                    backgroundImage: `url(${animationSprite})`,
                    backgroundSize: '300% 300%',
                    animation: 'sprite-animation 1.2s steps(1) infinite',
                }}
            />
            <p className="text-gray-600 font-medium">{message}</p>

            <style>{`
                @keyframes sprite-animation {
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
    );
}
