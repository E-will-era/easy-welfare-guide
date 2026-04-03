// API 기본 설정
const API_BASE_URL = "/api/v1";

/**
 * API 요청 유틸리티
 * @param {string} endpoint - API 엔드포인트 (/api/v1/...)
 * @param {object} options - fetch 옵션
 * @returns {Promise<any>} - JSON 응답
 */
export async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };

    const response = await fetch(url, mergedOptions);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new Error(errorData.detail || `API 요청 실패: ${response.status}`);
        error.status = response.status;
        error.data = errorData;
        throw error;
    }

    return response.json();
}

/**
 * GET 요청 헬퍼
 */
export function apiGet(endpoint, options = {}) {
    return apiRequest(endpoint, { ...options, method: 'GET' });
}

/**
 * POST 요청 헬퍼
 */
export function apiPost(endpoint, body, options = {}) {
    return apiRequest(endpoint, {
        ...options,
        method: 'POST',
        body: JSON.stringify(body),
    });
}

/**
 * SSE 스트림 구독 함수
 * @param {string} endpoint - SSE 엔드포인트
 * @param {object} callbacks - 콜백 함수들
 * @param {function} callbacks.onMessage - 메시지 수신 시 콜백 (data) => void
 * @param {function} callbacks.onError - 에러 발생 시 콜백 (error) => void
 * @param {function} callbacks.onComplete - 완료 시 콜백 (data) => void
 * @returns {function} - 구독 취소 함수
 */
export function subscribeSSE(endpoint, { onMessage, onError, onComplete }) {
    const url = `${API_BASE_URL}${endpoint}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            if (data.status === 'completed') {
                onComplete?.(data);
                eventSource.close();
            } else if (data.status === 'failed') {
                onError?.(new Error(data.data?.code || '처리 중 오류가 발생했습니다.'));
                eventSource.close();
            } else {
                onMessage?.(data);
            }
        } catch (err) {
            onError?.(err);
        }
    };

    eventSource.onerror = (err) => {
        onError?.(new Error('SSE 연결 오류가 발생했습니다.'));
        eventSource.close();
    };

    // 구독 취소 함수 반환
    return () => {
        eventSource.close();
    };
}

export default {
    get: apiGet,
    post: apiPost,
    request: apiRequest,
    subscribeSSE,
};
