import { useState, useCallback, useRef } from 'react';

// API 기본 URL
const API_BASE_URL = "/api/v1";

// API 엔드포인트
const ANALYZE_API_URL = `${API_BASE_URL}/analyze`;
const ANALYZE_TEXT_API_URL = `${API_BASE_URL}/analyze-text`;
const RE_ANALYZE_API_URL = `${API_BASE_URL}/retry`;

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

                                            // close/failed/error phase 처리: 에러 메시지와 함께 표시
                                            if (currentPhase === 'close' || currentPhase === 'failed' || currentPhase === 'error') {
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

                                        // error 이벤트: 로딩 중단 + 에러 UI 표시 (에러 페이지로 가지 않음)
                                        if (currentEvent === 'error') {
                                            const errorMsg = jsonData.data?.message || '처리 중 오류가 발생했습니다.';
                                            isClosedOrFailed = true;
                                            setPhase('failed');
                                            setErrorMessage(errorMsg);
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
     * 텍스트 직접 입력 분석 (OCR 없이)
     * @param {string} text - 분석할 텍스트
     * @returns {Promise<object>}
     */
    const fetchAnalyzeText = useCallback(async (text) => {
        if (!text || !text.trim()) {
            throw new Error('텍스트가 필요합니다.');
        }

        setLoading(true);
        setError(null);
        setPhase(null);
        setData(null);
        setErrorMessage(null);

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        try {
            const response = await fetch(ANALYZE_TEXT_API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalData = null;
            let isClosedOrFailed = false;

            return new Promise((resolve, reject) => {
                const processStream = async () => {
                    try {
                        let currentEvent = null;

                        while (true) {
                            const { done, value } = await reader.read();

                            if (done) {
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
                                if (line.startsWith('event: ')) {
                                    currentEvent = line.slice(7).trim();
                                    continue;
                                }

                                if (line.startsWith('data: ')) {
                                    try {
                                        const jsonData = JSON.parse(line.slice(6));

                                        if (currentEvent === 'progress' && jsonData.data?.phase) {
                                            const currentPhase = jsonData.data.phase;
                                            setPhase(currentPhase);

                                            if (currentPhase === 'close' || currentPhase === 'failed' || currentPhase === 'error') {
                                                isClosedOrFailed = true;
                                                if (jsonData.data?.message) {
                                                    setErrorMessage(jsonData.data.message);
                                                }
                                            }
                                        }

                                        if (currentEvent === 'completed') {
                                            finalData = jsonData;
                                            setData(jsonData);
                                            setPhase('completed');
                                        }

                                        // error 이벤트: 로딩 중단 + 에러 UI 표시 (에러 페이지로 가지 않음)
                                        if (currentEvent === 'error') {
                                            const errorMsg = jsonData.data?.message || '처리 중 오류가 발생했습니다.';
                                            isClosedOrFailed = true;
                                            setPhase('failed');
                                            setErrorMessage(errorMsg);
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
     * 2차 질의 (더 쉬운 표현으로 재요청)
     * @param {string} adminSummary - 1차 응답의 admin_summary
     * @returns {Promise<object>}
     */
    const fetchRetry = useCallback(async (adminSummary) => {
        if (!adminSummary) {
            throw new Error('admin_summary가 필요합니다.');
        }

        setLoading(true);
        setError(null);
        setPhase(null);
        setErrorMessage(null);

        // 이전 요청 취소
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        try {
            const response = await fetch(RE_ANALYZE_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ admin_summary: adminSummary }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalData = null;
            let isClosedOrFailed = false;

            return new Promise((resolve, reject) => {
                const processStream = async () => {
                    try {
                        let currentEvent = null;

                        while (true) {
                            const { done, value } = await reader.read();

                            if (done) {
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
                                if (line.startsWith('event: ')) {
                                    currentEvent = line.slice(7).trim();
                                    continue;
                                }

                                if (line.startsWith('data: ')) {
                                    try {
                                        const jsonData = JSON.parse(line.slice(6));

                                        if (currentEvent === 'progress' && jsonData.data?.phase) {
                                            const currentPhase = jsonData.data.phase;
                                            setPhase(currentPhase);

                                            if (currentPhase === 'close' || currentPhase === 'failed' || currentPhase === 'error') {
                                                isClosedOrFailed = true;
                                                if (jsonData.data?.message) {
                                                    setErrorMessage(jsonData.data.message);
                                                }
                                            }
                                        }

                                        if (currentEvent === 'completed') {
                                            finalData = jsonData;
                                            setData(jsonData);
                                            setPhase('completed');
                                        }

                                        // error 이벤트: 로딩 중단 + 에러 UI 표시
                                        if (currentEvent === 'error') {
                                            const errorMsg = jsonData.data?.message || '처리 중 오류가 발생했습니다.';
                                            isClosedOrFailed = true;
                                            setPhase('failed');
                                            setErrorMessage(errorMsg);
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
        fetchAnalyzeText,
        fetchRetry,
        reset,
    };
}

export default useAnalyze;
