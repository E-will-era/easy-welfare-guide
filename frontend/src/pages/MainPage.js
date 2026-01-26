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
import { useAnalyze } from '../hooks/useAnalyze';

export default function MainPage() {
    const [viewState, setViewState] = useState('input'); // 'input', 'loading', 'completed'
    const [inputType, setInputType] = useState('text'); // 'text', 'pdf', 'image'
    const [adminSummary, setAdminSummary] = useState('');
    const [textInput, setTextInput] = useState('');
    const [file, setFile] = useState(null);
    const [output, setOutput] = useState('');

    // SSE 기반 분석 API 훅 사용
    const { fetchAnalyze, reset: resetApi, phase } = useAnalyze();

    // Load state from sessionStorage on mount
    // Load state from sessionStorage and IndexedDB on mount
    React.useEffect(() => {
        const savedState = sessionStorage.getItem('appState');
        if (savedState) {
            try {
                const parsedState = JSON.parse(savedState);
                if (parsedState.viewState) setViewState(parsedState.viewState);
                if (parsedState.inputType) setInputType(parsedState.inputType);
                if (parsedState.textInput) setTextInput(parsedState.textInput);
                if (parsedState.output) setOutput(parsedState.output);
                if (parsedState.adminSummary) setAdminSummary(parsedState.adminSummary);
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
                output,
                adminSummary,
            };

            // 
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

    }, [viewState, inputType, textInput, file, output, adminSummary]);

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
            // SSE 기반 API 호출 (자동으로 스트림 구독)
            const response = await fetchAnalyze();

            if (response && response.status === 'completed' && response.data) {
                // plain_summary를 사용자에게 표시 (마크다운 형식)
                setOutput(response.data.plain_summary);
                // 재질의를 위해 admin_summary를 저장
                setAdminSummary(response.data.admin_summary);
                setViewState('completed');
            }
        } catch (err) {
            console.error('API 호출 오류:', err);
            setOutput(`오류가 발생했습니다: ${err.message}`);
            setAdminSummary(`오류가 발생했습니다: ${err.message}`);
            setViewState('completed');
        }
    };

    const handleRetry = () => {
        setViewState('input');
        setOutput('');
        setAdminSummary('');
        setTextInput('');
        setFile(null);
        resetApi(); // API 상태 초기화
        sessionStorage.removeItem('appState'); // Clear stored state on retry
        del('uploadedFile'); // Clear file from IDB
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
                                <button
                                    onClick={handleRetry}
                                    className="action-button mode-button-inactive"
                                >
                                    다른 질문하기
                                </button>
                            )}
                        </>
                    )}
                </div>

                {/* 결과 섹션 - 카드 외부 하단에 배치 */}
                {viewState === 'completed' && (
                    <div className="mt-6 animate-fade-in-up">
                        <ResultDisplay result={output} />
                    </div>
                )}
            </div>
        </div>
    );
}
