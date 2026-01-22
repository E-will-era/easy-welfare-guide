import React, { useState } from 'react';
import PageHeader from '../components/default/PageHeader';
import GuideSection from '../components/input/GuideSection';
import ResultDisplay from '../components/result/ResultDisplay';
import InputModeSelector from '../components/input/InputModeSelector';
import TextInput from '../components/input/TextInput';
import PdfUploader from '../components/input/PdfUploader';
import ImageUploader from '../components/input/ImageUploader';
import UserQuerySummary from '../components/result/UserQuerySummary';
import LoadingSpinner from '../components/result/LoadingSpinner';

export default function MainPage() {
    const [viewState, setViewState] = useState('input'); // 'input', 'loading', 'result'
    const [inputType, setInputType] = useState('text'); // 'text', 'pdf', 'image'
    const [textInput, setTextInput] = useState('');
    const [file, setFile] = useState(null);
    const [output, setOutput] = useState('');

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

    const handleSubmit = () => {
        setViewState('loading');

        // Mock API call simulation
        setTimeout(() => {
            let result = '분석 결과:\n\n';
            if (inputType === 'text' && textInput) {
                result += `입력하신 텍스트에 대한 분석 결과입니다.\n내용이 충실하며 복지 헤택 적용 가능성이 높습니다.`;
            } else if ((inputType === 'pdf' || inputType === 'image') && file) {
                result += `업로드하신 파일(${file.name}) 분석 결과입니다.\n문서 내용을 바탕으로 맞춤형 정보를 제공합니다.`;
            } else {
                result += `데이터가 입력되지 않았습니다.`;
            }
            setOutput(result);
            setViewState('result');
        }, 1500);
    };

    const handleRetry = () => {
        setViewState('input');
        setOutput('');
        setTextInput('');
        setFile(null);
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
                            <h2 className="text-xl font-semibold text-gray-800 mb-4 px-1">
                                입력
                            </h2>
                            <InputModeSelector currentMode={inputType} onModeChange={handleModeChange} />
                            <div className="input-area-fixed mb-4">
                                {inputType === 'text' && (
                                    <TextInput value={textInput} onChange={setTextInput} />
                                )}
                                {inputType === 'pdf' && (
                                    <PdfUploader file={file} onFileChange={handleFileChange} />
                                )}
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
                    {(viewState === 'loading' || viewState === 'result') && (
                        <>
                            <UserQuerySummary
                                type={inputType}
                                text={textInput}
                                file={file}
                            />

                            {/* 로딩 중일 때 스피너 표시 */}
                            {viewState === 'loading' && (
                                <LoadingSpinner />
                            )}

                            {/* 결과 나왔을 때 버튼 표시 */}
                            {viewState === 'result' && (
                                <button
                                    onClick={handleRetry}
                                    className="action-button mode-button-inactive"
                                >
                                    다시 질문하기
                                </button>
                            )}
                        </>
                    )}
                </div>

                {/* 결과 섹션 - 카드 외부 하단에 배치 */}
                {viewState === 'result' && (
                    <div className="mt-6 animate-fade-in-up">
                        <ResultDisplay result={output} />
                    </div>
                )}
            </div>
        </div>
    );
}
