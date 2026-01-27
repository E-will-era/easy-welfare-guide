import { useState, useCallback, useRef } from 'react';
import { apiPost, subscribeSSE } from '../Api.js';

// API 엔드포인트
const START_API_URL = '/api/v1/test/analyze/start';
const RETRY_API_URL = '/api/v1/test/analyze/retry/start';

/**
 * SSE 기반 분석 API 호출 훅
 * POST /api/v1/test/analyze/start → GET /api/v1/test/analyze/{task_id}/stream
 *
 * @returns {object} - { data, loading, error, phase, fetchAnalyze, reset }
 */
export function useAnalyze() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [phase, setPhase] = useState(null); // 현재 진행 단계

    const unsubscribeRef = useRef(null);

    /**
     * 1차 분석 시작 및 SSE 스트림 구독
     * @returns {Promise<object>}
     */
    const fetchAnalyze = useCallback(async () => {
        setLoading(true);
        setError(null);
        setPhase(null);
        setData(null);

        try {
            // 1차 분석 시작 요청
            const response = await apiPost(START_API_URL, {});

            if (response.status !== 'pending' || !response.data?.task_id) {
                throw new Error('분석 시작 요청 실패');
            }

            const { sse_stream_uri } = response.data;

            // SSE 스트림 구독
            return new Promise((resolve, reject) => {
                unsubscribeRef.current = subscribeSSE(sse_stream_uri, {
                    onMessage: (data) => {
                        if (data.status === 'processing' && data.data?.phase) {
                            setPhase(data.data.phase);
                        }
                    },
                    onError: (err) => {
                        setError(err.message);
                        setLoading(false);
                        reject(err);
                    },
                    onComplete: (completedData) => {
                        setData(completedData);
                        setPhase('completed');
                        setLoading(false);
                        resolve(completedData);
                    },
                });
            });
        } catch (err) {
            setError(err.message || 'API 요청 중 오류가 발생했습니다.');
            setLoading(false);
            throw err;
        }
    }, []);

    /**
     * 2차 질의 (답변 재생성) 및 SSE 스트림 구독
     * @param {string} adminSummary - 1차 분석의 admin_summary (필수)
     * @returns {Promise<object>}
     */
    const fetchRetryAnalyze = useCallback(async (adminSummary) => {
        if (!adminSummary) {
            throw new Error('admin_summary가 필요합니다.');
        }

        setLoading(true);
        setError(null);
        setPhase(null);
        setData(null);

        try {
            // 2차 질의 시작 요청
            const response = await apiPost(RETRY_API_URL, { admin_summary: adminSummary });

            if (response.status !== 'pending' || !response.data?.task_id) {
                throw new Error('2차 질의 시작 요청 실패');
            }

            const { sse_stream_uri } = response.data;

            // SSE 스트림 구독
            return new Promise((resolve, reject) => {
                unsubscribeRef.current = subscribeSSE(sse_stream_uri, {
                    onMessage: (data) => {
                        if (data.status === 'processing' && data.data?.phase) {
                            setPhase(data.data.phase);
                        }
                    },
                    onError: (err) => {
                        setError(err.message);
                        setLoading(false);
                        reject(err);
                    },
                    onComplete: (completedData) => {
                        setData(completedData);
                        setPhase('completed');
                        setLoading(false);
                        resolve(completedData);
                    },
                });
            });
        } catch (err) {
            setError(err.message || '2차 질의 중 오류가 발생했습니다.');
            setLoading(false);
            throw err;
        }
    }, []);

    /**
     * 상태 초기화 및 SSE 구독 해제
     */
    const reset = useCallback(() => {
        if (unsubscribeRef.current) {
            unsubscribeRef.current();
            unsubscribeRef.current = null;
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
        fetchRetryAnalyze,
        reset,
    };
}

export default useAnalyze;
