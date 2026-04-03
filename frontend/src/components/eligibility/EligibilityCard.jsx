import React from 'react';
import {
    Paper,
    Box,
    Typography,
    Button,
    CircularProgress,
    Chip,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

/**
 * 설명: 사용자의 앱 신청 혜택을 묻는 O/X 자격 문답 플로우들을 진행시키는 Card 통합 모듈.
 * 작동 방식: 백엔드 상태인 eligibilityStatus 값을 관측하여 각 대기/질문중/완료/오류 상이한 UI로 변경 렌더링 함.
 * 반환값: 현재 진행하고있는 상태의 UI 정보 렌더링을 뿜어내는 MUI 통합형 Paper 컴포넌트 객체 덩어리.
 */
export default function EligibilityCard({
    sessionId,
    programInfo,
    onStartCheck,
    onSubmitAnswer,
    eligibilityStatus,
    currentQuestion,
    determination,
    questionHistory,
    error,
    onRequestDocuments,
}) {

    /**
     * 설명: O/X 구문 자격 점검을 실시하는 시작 트리거 버튼 제어 코어 함수.
     * 작동 방식: Hook 부모 객체로부터 내려오는 session 데이터와 info 값들을 연결해주어 API 전달.
     * 반환값: void
     */
    const handleStart = () => {
        if (onStartCheck) {
            onStartCheck(sessionId, programInfo);
        }
    };

    /**
     * 설명: 유저의 O/X 제출 버튼 클릭시 해당 상태값을 답변으로 입력 제출.
     * 작동 방식: 불린(Boolean) 문자열 등의 answer 와 ID 를 부모 콜백으로 올려 보내어 백단 서버와 연동시킴.
     * 반환값: void
     */
    const handleAnswer = (answer) => {
        if (onSubmitAnswer) {
            onSubmitAnswer(sessionId, answer);
        }
    };

    /**
     * 설명: 최종 단의 "필요 서류 확인하기" 클릭을 관리하고 호출시킴.
     * 작동 방식: programInfo와 sessionId 값 정보 매체를 묶어서 상위 컴포넌트로 호출.
     * 반환값: void
     */
    const handleRequestDocs = () => {
        if (onRequestDocuments) {
            onRequestDocuments(programInfo, sessionId);
        }
    };

    // Compute progress text based on question history and remaining estimate
    const answeredCount = questionHistory ? questionHistory.length : 0;
    const remainingEstimate = currentQuestion?.remaining_questions_estimate ?? null;
    const totalEstimate = remainingEstimate != null ? answeredCount + 1 + remainingEstimate : null;
    const progressText = totalEstimate
        ? `질문 ${answeredCount + 1}/${totalEstimate}`
        : `질문 ${answeredCount + 1}`;

    return (
        <Paper
            elevation={0}
            sx={{
                borderRadius: '16px',
                p: { xs: 3, sm: 4 },
                bgcolor: 'rgba(255,255,255,0.95)',
                border: '2px solid #bfdbfe',
                boxShadow: '0 4px 20px -4px rgba(59, 130, 246, 0.15)',
            }}
        >
            {/* Card Header */}
            <Box className="flex items-center gap-2 mb-4">
                <SearchIcon sx={{ color: '#3b82f6', fontSize: 24 }} />
                <Typography
                    variant="h6"
                    sx={{ fontWeight: 700, color: '#1e3a5f', fontSize: '1.1rem' }}
                >
                    자격 여부 확인
                </Typography>
            </Box>

            {/* ── IDLE STATE: intro text + start button ── */}
            {eligibilityStatus === 'idle' && (
                <Box>
                    <Typography
                        variant="body2"
                        sx={{ color: '#4b5563', mb: 3, lineHeight: 1.7 }}
                    >
                        이 복지 제도의 대상이 되는지<br />
                        간단한 질문으로 확인해 보세요
                    </Typography>
                    <Button
                        fullWidth
                        variant="contained"
                        onClick={handleStart}
                        sx={{
                            py: 1.5,
                            borderRadius: '12px',
                            fontWeight: 700,
                            fontSize: '1rem',
                            textTransform: 'none',
                            background: 'linear-gradient(to right, #3b82f6, #0ea5e9)',
                            boxShadow: '0 4px 12px -2px rgba(59, 130, 246, 0.4)',
                            '&:hover': {
                                boxShadow: '0 8px 20px -4px rgba(59, 130, 246, 0.5)',
                            },
                        }}
                    >
                        자격 확인 시작하기
                    </Button>
                </Box>
            )}

            {/* ── LOADING STATE: spinner while fetching ── */}
            {eligibilityStatus === 'loading' && (
                <Box className="flex flex-col items-center py-6 gap-3">
                    <CircularProgress size={36} sx={{ color: '#3b82f6' }} />
                    <Typography variant="body2" sx={{ color: '#6b7280' }}>
                        확인 중입니다...
                    </Typography>
                </Box>
            )}

            {/* ── QUESTIONING STATE: show current question + O/X buttons ── */}
            {eligibilityStatus === 'questioning' && currentQuestion && (
                <Box>
                    {/* Progress indicator */}
                    <Box className="flex items-center justify-between mb-3">
                        <Chip
                            label={progressText}
                            size="small"
                            sx={{
                                bgcolor: '#eff6ff',
                                color: '#3b82f6',
                                fontWeight: 600,
                                fontSize: '0.75rem',
                                border: '1px solid #bfdbfe',
                            }}
                        />
                    </Box>

                    {/* Question text */}
                    <Typography
                        variant="body1"
                        sx={{
                            color: '#1f2937',
                            fontWeight: 500,
                            mb: 4,
                            lineHeight: 1.7,
                            fontSize: '1rem',
                        }}
                    >
                        {currentQuestion.question}
                    </Typography>

                    {/* O/X answer buttons */}
                    <Box className="flex gap-3">
                        {/* "예" (Yes / O) button */}
                        <Button
                            variant="contained"
                            onClick={() => handleAnswer('예')}
                            fullWidth
                            sx={{
                                py: 2,
                                borderRadius: '14px',
                                fontWeight: 700,
                                fontSize: '1.1rem',
                                textTransform: 'none',
                                background: 'linear-gradient(135deg, #22c55e, #16a34a)',
                                boxShadow: '0 4px 12px -2px rgba(34, 197, 94, 0.4)',
                                minHeight: 56,
                                '&:hover': {
                                    background: 'linear-gradient(135deg, #16a34a, #15803d)',
                                    boxShadow: '0 8px 20px -4px rgba(34, 197, 94, 0.5)',
                                },
                            }}
                        >
                            O&nbsp;&nbsp;예
                        </Button>

                        {/* "아니오" (No / X) button */}
                        <Button
                            variant="contained"
                            onClick={() => handleAnswer('아니오')}
                            fullWidth
                            sx={{
                                py: 2,
                                borderRadius: '14px',
                                fontWeight: 700,
                                fontSize: '1.1rem',
                                textTransform: 'none',
                                background: 'linear-gradient(135deg, #f97316, #ea580c)',
                                boxShadow: '0 4px 12px -2px rgba(249, 115, 22, 0.4)',
                                minHeight: 56,
                                '&:hover': {
                                    background: 'linear-gradient(135deg, #ea580c, #c2410c)',
                                    boxShadow: '0 8px 20px -4px rgba(249, 115, 22, 0.5)',
                                },
                            }}
                        >
                            X&nbsp;&nbsp;아니오
                        </Button>
                    </Box>
                </Box>
            )}

            {/* ── DETERMINED STATE: show result ── */}
            {eligibilityStatus === 'determined' && determination && (
                <Box>
                    {/* Verdict card - green if eligible, orange if not */}
                    <Box
                        sx={{
                            borderRadius: '12px',
                            p: 3,
                            mb: 3,
                            bgcolor: determination.eligible
                                ? 'rgba(220, 252, 231, 0.8)'
                                : 'rgba(255, 237, 213, 0.8)',
                            border: `2px solid ${determination.eligible ? '#86efac' : '#fdba74'}`,
                        }}
                    >
                        <Box className="flex items-center gap-2 mb-2">
                            {determination.eligible ? (
                                <CheckCircleIcon sx={{ color: '#16a34a', fontSize: 28 }} />
                            ) : (
                                <CancelIcon sx={{ color: '#ea580c', fontSize: 28 }} />
                            )}
                            <Typography
                                variant="h6"
                                sx={{
                                    fontWeight: 700,
                                    color: determination.eligible ? '#15803d' : '#c2410c',
                                    fontSize: '1.05rem',
                                }}
                            >
                                {determination.eligible ? '자격 있음' : '자격 없음'}
                                {determination.confidence != null && (
                                    <Typography
                                        component="span"
                                        sx={{
                                            fontWeight: 400,
                                            fontSize: '0.85rem',
                                            ml: 1,
                                            color: determination.eligible ? '#16a34a' : '#ea580c',
                                        }}
                                    >
                                        (신뢰도: {Math.round(determination.confidence * 100)}%)
                                    </Typography>
                                )}
                            </Typography>
                        </Box>

                        {determination.reason && (
                            <Typography
                                variant="body2"
                                sx={{
                                    color: determination.eligible ? '#166534' : '#9a3412',
                                    lineHeight: 1.6,
                                }}
                            >
                                근거: {determination.reason}
                            </Typography>
                        )}
                    </Box>

                    {/* Button to fetch document guide */}
                    <Button
                        fullWidth
                        variant="outlined"
                        onClick={handleRequestDocs}
                        sx={{
                            py: 1.5,
                            borderRadius: '12px',
                            fontWeight: 700,
                            fontSize: '0.95rem',
                            textTransform: 'none',
                            borderColor: '#3b82f6',
                            color: '#3b82f6',
                            '&:hover': {
                                borderColor: '#1d4ed8',
                                bgcolor: '#eff6ff',
                            },
                        }}
                    >
                        📋 필요 서류 확인하기
                    </Button>
                </Box>
            )}

            {/* ── ERROR STATE: error message + retry option ── */}
            {eligibilityStatus === 'error' && (
                <Box>
                    <Box className="flex items-center gap-2 mb-3">
                        <ErrorOutlineIcon sx={{ color: '#ef4444', fontSize: 22 }} />
                        <Typography variant="body2" sx={{ color: '#ef4444', fontWeight: 600 }}>
                            오류가 발생했습니다
                        </Typography>
                    </Box>
                    {error && (
                        <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
                            {error}
                        </Typography>
                    )}
                    <Button
                        fullWidth
                        variant="outlined"
                        onClick={handleStart}
                        sx={{
                            py: 1.5,
                            borderRadius: '12px',
                            fontWeight: 700,
                            fontSize: '0.95rem',
                            textTransform: 'none',
                            borderColor: '#3b82f6',
                            color: '#3b82f6',
                            '&:hover': {
                                borderColor: '#1d4ed8',
                                bgcolor: '#eff6ff',
                            },
                        }}
                    >
                        다시 시도하기
                    </Button>
                </Box>
            )}
        </Paper>
    );
}
