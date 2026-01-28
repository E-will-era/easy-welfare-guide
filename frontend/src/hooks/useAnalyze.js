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

            return new Promise((resolve, reject) => {
                const processStream = async () => {
                    try {
                        let currentEvent = null;

                        while (true) {
                            const { done, value } = await reader.read();

                            if (done) {
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
                                            setPhase(jsonData.data.phase);
                                        }

                                        // completed 이벤트: 최종 데이터 저장
                                        if (currentEvent === 'completed') {
                                            finalData = jsonData;
                                            setData(jsonData);
                                            setPhase('completed');
                                        }

                                        // error 이벤트: 에러 처리
                                        if (currentEvent === 'error') {
                                            const errorMsg = jsonData.data?.message || '처리 중 오류가 발생했습니다.';
                                            setError(errorMsg);
                                            setLoading(false);
                                            reject(new Error(errorMsg));
                                            return;
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
    }, []);

    return {
        data,
        loading,
        error,
        phase,
        fetchAnalyze,
        reset,
    };
}

export default useAnalyze;
