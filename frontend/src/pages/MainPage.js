import React, { useState } from 'react';
import { set, get, del } from 'idb-keyval';
import { Box, Container, Paper, Button, GlobalStyles } from '@mui/material';
import PageHeader from '../components/default/PageHeader';
import GuideSection from '../components/input/GuideSection';
import ResultDisplay from '../components/result/ResultDisplay';
import InputModeSelector from '../components/input/InputModeSelector';
import TextInput from '../components/input/TextInput';
import ImageUploader from '../components/input/ImageUploader';
import UserQuerySummary from '../components/result/UserQuerySummary';
import ServiceIntroModal from '../components/default/ServiceIntroModal';
import GhostButton from '../components/ui/GhostButton';
import LoadingSpinner from '../components/result/LoadingSpinner';
import SecondLoadingSpinner from '../components/result/SecondLoadingSpinner';
import ServiceReference from '../components/result/ServiceReference';
import FeedbackLoopSelector from '../components/result/FeedbackLoopSelector';
import AskOtherWorkSelector from '../components/result/AskOtherWorkSelector';
import { useAnalyze } from '../hooks/useAnalyze';
import InfoIcon from '@mui/icons-material/Info';
import FavoriteIcon from '@mui/icons-material/Favorite';
import Footer from '../components/default/Footer';

const globalStyles = (
    <GlobalStyles styles={{
        '@keyframes fadeIn': {
            from: { opacity: 0, transform: 'translateY(-20px)' },
            to: { opacity: 1, transform: 'translateY(0)' }
        },
        '@keyframes fadeInUp': {
            from: { opacity: 0, transform: 'translateY(20px)' },
            to: { opacity: 1, transform: 'translateY(0)' }
        },
        '.animate-fade-in': { animation: 'fadeIn 0.8s ease-out' },
        '.animate-fade-in-up': { animation: 'fadeInUp 0.6s ease-out' }
    }} />
);

export default function MainPage({ onError }) {
    const [viewState, setViewState] = useState('input');
    const [inputType, setInputType] = useState('text');
    const [adminSummary, setAdminSummary] = useState('');
    const [textInput, setTextInput] = useState('');
    const [file, setFile] = useState(null);
    const [isIntroModalOpen, setIsIntroModalOpen] = useState(false);

    const [firstResponse, setFirstResponse] = useState(null);
    const [secondResponse, setSecondResponse] = useState(null);
    const [questionCount, setQuestionCount] = useState(0);
    const [showReferences, setShowReferences] = useState(false);
    const [retryLoading, setRetryLoading] = useState(false); // 2차 질의 로딩 상태
    const [retryError, setRetryError] = useState(false); // 2차 질의 에러 상태
    const [retryErrorMessage, setRetryErrorMessage] = useState(null); // 2차 질의 에러 메시지

    const { fetchAnalyze, fetchRetry, reset: resetApi, phase, errorMessage } = useAnalyze();

    React.useEffect(() => {
        const savedState = sessionStorage.getItem('appState');
        if (savedState) {
            try {
                const parsedState = JSON.parse(savedState);
                if (parsedState.viewState) setViewState(parsedState.viewState);
                if (parsedState.inputType) setInputType(parsedState.inputType);
                if (parsedState.textInput) setTextInput(parsedState.textInput);
                if (parsedState.adminSummary) setAdminSummary(parsedState.adminSummary);
                if (parsedState.firstResponse) setFirstResponse(parsedState.firstResponse);
                if (parsedState.secondResponse) setSecondResponse(parsedState.secondResponse);
                if (parsedState.questionCount !== undefined) setQuestionCount(parsedState.questionCount);
                if (parsedState.showReferences !== undefined) setShowReferences(parsedState.showReferences);
            } catch (e) {
                console.error("Failed to load state:", e);
                sessionStorage.removeItem('appState');
            }
        }

        get('uploadedFile').then((val) => {
            if (val) setFile(val);
        });
    }, []);

    React.useEffect(() => {
        const _saveState = async () => {
            const stateToSave = {
                viewState,
                inputType,
                textInput,
                adminSummary,
                firstResponse,
                secondResponse,
                questionCount,
                showReferences,
            };

            try {
                sessionStorage.setItem('appState', JSON.stringify(stateToSave));
            } catch (e) {
                console.error("Failed to save session state:", e);
            }

            if (file) {
                set('uploadedFile', file).catch(err => console.error("Failed to save file to IDB", err));
            } else {
                del('uploadedFile');
            }
        };

        const timeoutId = setTimeout(_saveState, 500);
        return () => clearTimeout(timeoutId);

    }, [viewState, inputType, textInput, file, adminSummary, firstResponse, secondResponse, questionCount, showReferences]);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
        }
    };

    const handleModeChange = (mode) => {
        setInputType(mode);
        setTextInput('');
        setFile(null);
    };

    const handleSubmit = async () => {
        if (!file) {
            console.error('파일이 선택되지 않았습니다.');
            return;
        }

        setViewState('loading');

        try {
            const response = await fetchAnalyze(file);

            if (response) {
                setFirstResponse({
                    plain_summary: response.plain_summary || response.result?.plain_summary,
                    references: response.references || response.result?.references || []
                });
                setAdminSummary(response.admin_summary || response.result?.admin_summary || '');
                setQuestionCount(1);
                setViewState('completed');
            }
            // response가 null이면 (close/failed phase) viewState는 loading 유지 → 에러 UI 표시
        } catch (err) {
            console.error('API 호출 오류:', err);
            // phase가 close/failed면 에러 페이지로 가지 않고 로딩 화면에서 에러 UI 표시
            if (phase === 'close' || phase === 'failed') {
                return; // viewState는 loading 유지
            }
            const statusCode = err.status || 500;
            if (onError) {
                onError(statusCode);
            }
        }
    };

    const handleRetryQuestion = async () => {
        if (!adminSummary) {
            console.error('admin_summary가 없습니다.');
            setShowReferences(true);
            return;
        }

        // 2차 질의 시작 - viewState는 completed 유지, retryLoading만 true
        setRetryLoading(true);
        setRetryError(false);

        try {
            const response = await fetchRetry(adminSummary);

            if (response) {
                setSecondResponse({
                    plain_summary: response.retry_plain_summary || response.plain_summary,
                    references: firstResponse?.references || []
                });
                setQuestionCount(2);
                setRetryLoading(false);
            } else {
                // response가 null이면 (close/failed/error phase) 에러 상태로 전환
                setRetryLoading(false);
                setRetryError(true);
                setShowReferences(true); // 에러 시 참고자료 표시
            }
        } catch (err) {
            console.error('2차 질의 오류:', err);
            setRetryLoading(false);
            setRetryError(true);
            setShowReferences(true); // 에러 시 참고자료 표시
        }
    };

    const handleRetry = () => {
        setViewState('input');
        setAdminSummary('');
        setTextInput('');
        setFile(null);
        setFirstResponse(null);
        setSecondResponse(null);
        setQuestionCount(0);
        setShowReferences(false);
        setRetryLoading(false);
        setRetryError(false);
        resetApi();
        sessionStorage.removeItem('appState');
        del('uploadedFile');
    };

    const handleGoToWelfareCenter = () => {
        window.open('https://www.129.go.kr/', '_blank', 'noopener,noreferrer');
    };

    const handleSatisfied = () => {
        setShowReferences(true);
    };

    return (
        <Box sx={{
            minHeight: '100vh',
            background: 'linear-gradient(to bottom right, #e0f2fe, #eff6ff, #cffafe)',
            position: 'relative',
            overflow: 'hidden',
            pb: '100px'
        }}>
            {globalStyles}

            {/* Service Intro Button */}
            <Box sx={{ position: 'fixed', zIndex: 100 }}>
                {/* Mobile FAB - Footer 위에 위치 */}
                <Box sx={{ display: { xs: 'block', sm: 'none' }, position: 'fixed', bottom: 60, right: 16 }}>
                    <GhostButton
                        label="서비스 소개"
                        Icon={InfoIcon}
                        onClick={() => setIsIntroModalOpen(true)}
                        isFab={true}
                    />
                </Box>
                {/* Desktop Button */}
                <Box sx={{ display: { xs: 'none', sm: 'block' }, position: 'fixed', top: 24, right: 24 }}>
                    <Button
                        onClick={() => setIsIntroModalOpen(true)}
                        sx={{
                            bgcolor: 'rgba(255,255,255,0.7)',
                            backdropFilter: 'blur(8px)',
                            color: '#1d4ed8',
                            px: 3,
                            py: 1,
                            borderRadius: '50px',
                            boxShadow: 2,
                            textTransform: 'none',
                            fontWeight: 600,
                            '&:hover': {
                                bgcolor: 'rgba(255,255,255,0.9)',
                            }
                        }}
                        startIcon={<FavoriteIcon sx={{ color: '#3b82f6' }} />}
                    >
                        서비스 소개
                    </Button>
                </Box>
            </Box>

            <ServiceIntroModal
                isOpen={isIntroModalOpen}
                onClose={() => setIsIntroModalOpen(false)}
            />

            <Container maxWidth="sm" sx={{ position: 'relative', zIndex: 10, pt: 4, px: 2 }}>
                {/* Main Card */}
                <Paper
                    elevation={0}
                    sx={{
                        borderRadius: '24px',
                        p: { xs: 3, sm: 4 },
                        bgcolor: 'rgba(255,255,255,0.9)',
                        backdropFilter: 'blur(12px)',
                        border: '2px solid #bfdbfe',
                        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
                        position: 'relative',
                        overflow: 'visible',
                        transition: 'all 0.7s',
                    }}
                    className="animate-fade-in"
                >
                    <PageHeader />

                    {viewState === 'input' && (
                        <>
                            <GuideSection />
                            <InputModeSelector currentMode={inputType} onModeChange={handleModeChange} />

                            <Box sx={{ minHeight: 200, mb: 3 }}>
                                {inputType === 'text' && (
                                    <TextInput value={textInput} onChange={setTextInput} />
                                )}
                                {inputType === 'image' && (
                                    <ImageUploader file={file} onFileChange={handleFileChange} />
                                )}
                            </Box>
                            <Button
                                fullWidth
                                variant="contained"
                                onClick={handleSubmit}
                                disabled={
                                    (inputType === 'text' && !textInput.trim()) ||
                                    ((inputType === 'pdf' || inputType === 'image') && !file)
                                }
                                sx={{
                                    py: 2.5,
                                    borderRadius: '16px',
                                    fontWeight: 700,
                                    fontSize: '1.1rem',
                                    textTransform: 'none',
                                    background: 'linear-gradient(to right, #3b82f6, #0ea5e9, #06b6d4)',
                                    boxShadow: '0 10px 30px -5px rgba(59, 130, 246, 0.4)',
                                    position: 'relative',
                                    overflow: 'hidden',
                                    '&:hover': {
                                        boxShadow: '0 20px 40px -5px rgba(59, 130, 246, 0.5)',
                                    },
                                    '&.Mui-disabled': {
                                        background: '#e5e7eb',
                                        color: '#9ca3af',
                                        boxShadow: 'none'
                                    },
                                    '&::after': {
                                        content: '""',
                                        position: 'absolute',
                                        inset: 0,
                                        background: 'linear-gradient(to right, transparent, rgba(255,255,255,0.3), transparent)',
                                        transform: 'translateX(-100%)',
                                        transition: 'transform 1s'
                                    },
                                    '&:hover::after': {
                                        transform: 'translateX(100%)'
                                    }
                                }}
                            >
                                제출하기
                            </Button>
                        </>
                    )}

                    {(viewState === 'loading' || viewState === 'completed') && (
                        <>
                            <UserQuerySummary
                                type={inputType}
                                text={textInput}
                                file={file}
                            />

                            {viewState === 'loading' && (
                                <LoadingSpinner phase={phase} errorMessage={errorMessage} onRetry={handleRetry} />
                            )}
                        </>
                    )}
                </Paper>

                {/* Results Section */}
                {viewState === 'completed' && (
                    <Box sx={{ mt: 4 }} className="animate-fade-in-up">
                        {firstResponse && (
                            <ResultDisplay
                                result={firstResponse.plain_summary}
                                references={firstResponse.references}
                                label="1차 답변"
                                isFirst={true}
                            />
                        )}

                        {/* 2차 질의 로딩 중 */}
                        {retryLoading && (
                            <Box sx={{ mt: 3 }}>
                                <SecondLoadingSpinner phase={phase} errorMessage={errorMessage} />
                            </Box>
                        )}

                        {/* 2차 질의 에러 시 */}
                        {retryError && !retryLoading && (
                            <Box sx={{ mt: 3 }}>
                                <SecondLoadingSpinner phase="error" errorMessage={retryErrorMessage} />
                            </Box>
                        )}

                        {/* 2차 답변 표시 */}
                        {secondResponse && !retryLoading && !retryError && (
                            <Box sx={{ mt: 3 }}>
                                <ResultDisplay
                                    result={secondResponse.plain_summary}
                                    references={secondResponse.references}
                                    label="2차 답변"
                                    isFirst={false}
                                />
                            </Box>
                        )}
                    </Box>
                )}

                {/* Feedback Section - 2차 질의 로딩 중이 아니고, 에러도 아닐 때만 표시 */}
                {viewState === 'completed' && questionCount < 2 && !showReferences && !retryLoading && !retryError && (
                    <Box sx={{ mt: 4 }} className="animate-fade-in-up">
                        <FeedbackLoopSelector
                            onYes={handleSatisfied}
                            onNo={handleRetryQuestion}
                        />
                    </Box>
                )}

                {/* References & Retry Section - 2차 완료, showReferences, 또는 2차 에러 시 표시 */}
                {viewState === 'completed' && (showReferences || questionCount >= 2 || retryError) && !retryLoading && (
                    <>
                        <ServiceReference
                            references={firstResponse?.references || []}
                        />
                        <Box sx={{ mt: 2 }} className="animate-fade-in-up">
                            <AskOtherWorkSelector
                                onRetry={handleRetry}
                                onOtherWork={handleGoToWelfareCenter}
                            />
                        </Box>
                    </>
                )}

            </Container>

            <Footer />
        </Box>
    );
}
