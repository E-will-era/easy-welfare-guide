import { useState, useCallback, useRef } from 'react';

// API 기본 URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// API 엔드포인트
const ANALYZE_API_URL = `${API_BASE_URL}/api/v1/analyze`;

/**
 * SSE 기반 복지 문서 분석 API 호출 훅
 * POST /api/v1/analyze (multipart/form-data) → SSE 스트리밍 응답
 *
 * @returns {object} - { data, loading, error, phase, fetchAnalyze, reset }
 */
export function useAnalyze() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [phase, setPhase] = useState(null); // 현재 진행 단계
    const [errorMessage, setErrorMessage] = useState(null); // close/failed 시 백엔드에서 전달된 메시지

    const abortControllerRef = useRef(null);

    /**
     * 파일 업로드 및 SSE 스트림 분석
     * @param {File} file - 분석할 파일
     * @returns {Promise<object>}
     */
    const fetchAnalyze = useCallback(async (file) => {
        if (!file) {
            throw new Error('파일이 필요합니다.');
        }

        setLoading(true);
        setError(null);
        setPhase(null);
        setData(null);
        setErrorMessage(null);

        // 이전 요청 취소
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(ANALYZE_API_URL, {
                method: 'POST',
                body: formData,
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalData = null;
            let isClosedOrFailed = false; // close/failed phase 여부 추적

            return new Promise((resolve, reject) => {
                const processStream = async () => {
                    try {
                        let currentEvent = null;

                        while (true) {
                            const { done, value } = await reader.read();

                            if (done) {
                                // close/failed 상태면 로딩 유지하고 resolve하지 않음 (에러 UI 계속 표시)
                                if (isClosedOrFailed) {
                                    setLoading(false);
                                    resolve(null);
                                    break;
                                }
                                setPhase('completed');
                                setLoading(false);
                                resolve(finalData);
                                break;
                            }

                            buffer += decoder.decode(value, { stream: true });
                            const lines = buffer.split('\n');
                            buffer = lines.pop() || '';

                            for (const line of lines) {
                                // event 타입 파싱
                                if (line.startsWith('event: ')) {
                                    currentEvent = line.slice(7).trim();
                                    continue;
                                }

                                // data 파싱
                                if (line.startsWith('data: ')) {
                                    try {
                                        const jsonData = JSON.parse(line.slice(6));

                                        // progress 이벤트: phase 업데이트
                                        if (currentEvent === 'progress' && jsonData.data?.phase) {
                                            const currentPhase = jsonData.data.phase;
                                            setPhase(currentPhase);

                                            // close/failed phase 처리: 에러 메시지와 함께 표시
                                            if (currentPhase === 'close' || currentPhase === 'failed') {
                                                isClosedOrFailed = true;
                                                if (jsonData.data?.message) {
                                                    setErrorMessage(jsonData.data.message);
                                                }
                                                // 로딩은 유지하되 스트림은 계속 처리
                                            }
                                        }

                                        // completed 이벤트: 최종 데이터 저장
                                        if (currentEvent === 'completed') {
                                            finalData = jsonData;
                                            setData(jsonData);
                                            setPhase('completed');
                                        }

                                        // error 이벤트: 에러 처리
                                        if (currentEvent === 'error') {
                                            const errorPhase = jsonData.data?.phase;
                                            const errorMsg = jsonData.data?.message || '처리 중 오류가 발생했습니다.';

                                            // close/failed phase면 에러 UI로 표시 (에러 페이지로 가지 않음)
                                            if (errorPhase === 'close' || errorPhase === 'failed') {
                                                isClosedOrFailed = true;
                                                setPhase(errorPhase);
                                                setErrorMessage(errorMsg);
                                                // 스트림 종료 대기
                                            } else {
                                                // 그 외 에러는 기존대로 처리
                                                setError(errorMsg);
                                                setLoading(false);
                                                reject(new Error(errorMsg));
                                                return;
                                            }
                                        }
                                    } catch (parseErr) {
                                        // JSON 파싱 실패 시 무시
                                    }
                                    currentEvent = null;
                                }
                            }
                        }
                    } catch (streamErr) {
                        if (streamErr.name === 'AbortError') {
                            return;
                        }
                        setError(streamErr.message);
                        setLoading(false);
                        reject(streamErr);
                    }
                };

                processStream();
            });
        } catch (err) {
            if (err.name === 'AbortError') {
                return;
            }
            setError(err.message || 'API 요청 중 오류가 발생했습니다.');
            setLoading(false);
            throw err;
        }
    }, []);

    /**
     * 상태 초기화 및 요청 취소
     */
    const reset = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
        setData(null);
        setLoading(false);
        setError(null);
        setPhase(null);
        setErrorMessage(null);
    }, []);

    return {
        data,
        loading,
        error,
        phase,
        errorMessage,
        fetchAnalyze,
        reset,
    };
}

export default useAnalyze;
