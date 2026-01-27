import React, { useState } from 'react';
import { set, get, del } from 'idb-keyval';
import PageHeader from '../components/default/PageHeader';
import GuideSection from '../components/input/GuideSection';
import ResultDisplay from '../components/result/ResultDisplay';
import InputModeSelector from '../components/input/InputModeSelector';
import TextInput from '../components/input/TextInput';
import ImageUploader from '../components/input/ImageUploader';
import UserQuerySummary from '../components/result/UserQuerySummary';
import LoadingSpinner from '../components/result/LoadingSpinner';
import ServiceReference from '../components/result/ServiceReference';
import FeedbackLoopSelector from '../components/result/FeedbackLoopSelector';
import { useAnalyze } from '../hooks/useAnalyze';

export default function MainPage() {
    const [viewState, setViewState] = useState('input'); // 'input', 'loading', 'completed'
    const [inputType, setInputType] = useState('text'); // 'text', 'pdf', 'image'
    const [adminSummary, setAdminSummary] = useState('');
    const [textInput, setTextInput] = useState('');
    const [file, setFile] = useState(null);

    // 1차/2차 답변 분리 저장
    const [firstResponse, setFirstResponse] = useState(null);  // { plain_summary, references }
    const [secondResponse, setSecondResponse] = useState(null); // { plain_summary, references }
    const [questionCount, setQuestionCount] = useState(0); // 0: 미질문, 1: 1차 완료, 2: 2차 완료
    const [showReferences, setShowReferences] = useState(false); // "네" 선택 시 references 표시

    // SSE 기반 분석 API 훅 사용
    const { fetchAnalyze, fetchRetryAnalyze, reset: resetApi, phase } = useAnalyze();

    // Load state from sessionStorage and IndexedDB on mount
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

        // Load file from IndexedDB
        get('uploadedFile').then((val) => {
            if (val) setFile(val);
        });
    }, []);

    // Save state to sessionStorage and IndexedDB on change
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

            // Save file to IndexedDB
            if (file) {
                set('uploadedFile', file).catch(err => console.error("Failed to save file to IDB", err));
            } else {
                del('uploadedFile');
            }
        };

        const timeoutId = setTimeout(_saveState, 500); // Debounce saves
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
        // We can optionally clear storage here, but the useEffect will update it soon anyway with nulls
    };

    const handleSubmit = async () => {
        setViewState('loading');

        try {
            // SSE 기반 API 호출 (1차 질의)
            const response = await fetchAnalyze();

            if (response && response.status === 'completed' && response.data) {
                // 1차 답변 저장
                setFirstResponse({
                    plain_summary: response.data.plain_summary,
                    references: response.data.references || []
                });
                // 재질의를 위해 admin_summary를 저장
                setAdminSummary(response.data.admin_summary);
                setQuestionCount(1);
                setViewState('completed');
            }
        } catch (err) {
            console.error('API 호출 오류:', err);
            setFirstResponse({
                plain_summary: `오류가 발생했습니다: ${err.message}`,
                references: []
            });
            setQuestionCount(1);
            setViewState('completed');
        }
    };

    const handleRetryQuestion = async () => {
        // 2차까지만 허용
        if (questionCount >= 2) return;

        setViewState('loading');

        try {
            // 저장된 adminSummary를 사용하여 2차 질의 (답변 재생성)
            const response = await fetchRetryAnalyze(adminSummary);

            if (response && response.status === 'completed' && response.data) {
                // 2차 답변 저장
                setSecondResponse({
                    plain_summary: response.data.plain_summary
                });
                setQuestionCount(2);
                setViewState('completed');
            }
        } catch (err) {
            console.error('2차 질의 API 호출 오류:', err);
            setSecondResponse({
                plain_summary: `오류가 발생했습니다: ${err.message}`,
                references: []
            });
            setQuestionCount(2);
            setViewState('completed');
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
        resetApi(); // API 상태 초기화
        sessionStorage.removeItem('appState'); // Clear stored state on retry
        del('uploadedFile'); // Clear file from IDB
    };

    // "네, 충분해요" 선택 시 - references 표시
    const handleSatisfied = () => {
        setShowReferences(true);
    };

    return (
        <div className="main-page-container">
            <div className="w-full max-w-lg">
                <div className="unified-card">
                    {/* 타이틀 (항상 표시) */}
                    <PageHeader />

                    {/* 입력 모드 */}
                    {viewState === 'input' && (
                        <>
                            <GuideSection />
                            <InputModeSelector currentMode={inputType} onModeChange={handleModeChange} />
                            <div className="input-area-fixed mb-4">
                                {inputType === 'text' && (
                                    <TextInput value={textInput} onChange={setTextInput} />
                                )}
                                {/*pdf 파일 사용 시 주석 해제
                                    {inputType === 'pdf' && (
                                    <PdfUploader file={file} onFileChange={handleFileChange} />
                                )}*/}
                                {inputType === 'image' && (
                                    <ImageUploader file={file} onFileChange={handleFileChange} />
                                )}
                            </div>
                            <button
                                onClick={handleSubmit}
                                disabled={
                                    (inputType === 'text' && !textInput.trim()) ||
                                    ((inputType === 'pdf' || inputType === 'image') && !file)
                                }
                                className={`action-button ${(inputType === 'text' && !textInput.trim()) ||
                                    ((inputType === 'pdf' || inputType === 'image') && !file)
                                    ? 'action-button-disabled'
                                    : 'action-button-primary'
                                    }`}
                            >
                                제출하기
                            </button>
                        </>
                    )}

                    {/* 로딩 및 결과 모드 (요약 항상 표시) */}
                    {(viewState === 'loading' || viewState === 'completed') && (
                        <>
                            <UserQuerySummary
                                type={inputType}
                                text={textInput}
                                file={file}
                            />

                            {/* 로딩 중일 때 스피너 표시 */}
                            {viewState === 'loading' && (
                                <LoadingSpinner phase={phase} />
                            )}

                            {/* 결과 나왔을 때 버튼 표시 */}
                            {viewState === 'completed' && (
                                <div className="flex gap-3 justify-center w-full">
                                    <button
                                        onClick={handleRetry}
                                        className="action-button mode-button-inactive flex-1"
                                    >
                                        다른 질문하기
                                    </button>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* 결과 섹션 - 카드 외부 하단에 배치 */}
                {viewState === 'completed' && (
                    <div className="mt-6 animate-fade-in-up">
                        {/* 1차 답변 */}
                        {firstResponse && (
                            <ResultDisplay
                                result={firstResponse.plain_summary}
                                references={firstResponse.references}
                                label="1차 답변"
                                isFirst={true}
                            />
                        )}

                        {/* 2차 답변 */}
                        {secondResponse && (
                            <div className="mt-4">
                                <ResultDisplay
                                    result={secondResponse.plain_summary}
                                    references={secondResponse.references}
                                    label="2차 답변"
                                    isFirst={false}
                                />
                            </div>
                        )}
                    </div>
                )}

                {/* 피드백 선택 - 2차 미만이고 아직 "네" 선택 안 했을 때 */}
                {viewState === 'completed' && questionCount < 2 && !showReferences && (
                    <div className="mt-6 animate-fade-in-up">
                        <FeedbackLoopSelector
                            onYes={handleSatisfied}
                            onNo={handleRetryQuestion}
                        />
                    </div>
                )}

                {/* "네" 선택 시 또는 2차 완료 후 reference 링크 안내 */}
                {viewState === 'completed' && (showReferences || questionCount >= 2) && (
                    <ServiceReference
                        references={firstResponse?.references || []}
                    />
                )}
            </div>
        </div>
    );
}
