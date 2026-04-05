import { useState, useCallback } from 'react';

// API base URL
const API_BASE_URL = "/api/v1";

// API endpoint URLs
const ELIGIBILITY_START_URL = `${API_BASE_URL}/eligibility/start`;
const ELIGIBILITY_ANSWER_URL = `${API_BASE_URL}/eligibility/answer`;
const DOCUMENTS_GUIDE_URL = `${API_BASE_URL}/documents/guide`;

/**
 * 설명: 자격 요건 판별 체크 및 관련 필요 문서 도큐먼트 가이드 API 통신을 전담하는 커스텀 Hook 모듈.
 * 작동 방식: 세션별로 여러 번에 걸쳐 수행되는 복수의 자격판별 문답 질의 체인을 관제 상태화.
 *   백엔드의 /eligibility/start 및 answer, /documents/guide 등의 노드 포인트를 참조함.
 * 반환값: React state들과 외부에서 작동 지시를 시그널 주는 action 제어 메소드.
 */
export function useEligibility() {
    // Status of the eligibility check flow
    // 'idle' | 'loading' | 'questioning' | 'determined' | 'error'
    const [eligibilityStatus, setEligibilityStatus] = useState('idle');

    // Current question from the backend
    // Shape: { question, question_field, remaining_questions_estimate }
    const [currentQuestion, setCurrentQuestion] = useState(null);

    // Final determination result from the backend
    // Shape: { eligible, confidence, reason }
    const [determination, setDetermination] = useState(null);

    // Document guide data fetched after determination
    // Shape: { program_name, documents[], application_info, tips[] }
    const [documents, setDocuments] = useState(null);

    // History of questions and answers in the current session
    // Each entry: { question, answer, field }
    const [questionHistory, setQuestionHistory] = useState([]);

    // Error message string, or null when no error
    const [error, setError] = useState(null);

    // State for separate document loading indicator
    const [documentLoading, setDocumentLoading] = useState(false);

    /**
     * 설명: 유저 정보 확인용 자격 체크 플로우를 초기업화 하고 스타트 시킵니다.
     * 작동 방식: POST요청을 통해 session 및 info 매개변수를 전송하고 들어온 즉각의 첫번째 질의문을 세팅.
     * 반환값: Promise 객체로서 작동 성공시 객체 배출, 실패일경우 null과 state기록 처리.
     * 예외: 코드의 중단을 방해하는 throw 유발대신 리액트의 에러 제어 상태로 감지 제어됨.
     */
    const startCheck = useCallback(async (sessionId, programInfo) => {
        if (!sessionId || !programInfo) {
            setError('세션 ID 또는 프로그램 정보가 없습니다.');
            setEligibilityStatus('error');
            return null;
        }

        setEligibilityStatus('loading');
        setError(null);
        setCurrentQuestion(null);
        setDetermination(null);
        setDocuments(null);
        setQuestionHistory([]);

        try {
            const response = await fetch(ELIGIBILITY_START_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    program_info: programInfo,
                }),
            });

            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }

            const raw = await response.json();
            // Unwrap the {"status":"ok","data":{...}} envelope from the backend
            const data = raw.data || raw;

            // Backend may return a question to ask, or an immediate determination
            if (data.status === 'questioning' && data.question) {
                setCurrentQuestion(data);
                setEligibilityStatus('questioning');
            } else if (data.status === 'determined') {
                setDetermination(data);
                setEligibilityStatus('determined');
            } else {
                // Fallback: treat any question field as a question response
                if (data.question) {
                    setCurrentQuestion(data);
                    setEligibilityStatus('questioning');
                } else {
                    throw new Error('예상치 못한 응답 형식입니다.');
                }
            }

            return data;
        } catch (err) {
            setError(err.message || '자격 확인 시작 중 오류가 발생했습니다.');
            setEligibilityStatus('error');
            return null;
        }
    }, []);

    /**
     * 설명: 사용자에의해 골립된 답변(예/아니오)을 현재 질문의 체인값으로 밀어 제출합니다.
     * 작동 방식: 서버로 세션ID값과 함께 결과 POST 발송, 판독된 status 정보를 통해 다음 문제로 
     *   진로를 옮기거나 결론지어졌다면 결정(determination) 처리를 내림.
     * 반환값: Promise 객체.
     * 예외: 리액트 에러 상태로 감지.
     */
    const submitAnswer = useCallback(async (sessionId, answer) => {
        if (!sessionId) {
            setError('세션 ID가 없습니다.');
            setEligibilityStatus('error');
            return null;
        }

        // Save the current question into history before moving on
        setQuestionHistory(prev => {
            const lastQuestion = currentQuestion;
            if (lastQuestion) {
                return [...prev, {
                    question: lastQuestion.question,
                    answer,
                    field: lastQuestion.question_field,
                }];
            }
            return prev;
        });

        setEligibilityStatus('loading');
        setError(null);

        try {
            const response = await fetch(ELIGIBILITY_ANSWER_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    answer,
                }),
            });

            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }

            const raw = await response.json();
            // Unwrap the {"status":"ok","data":{...}} envelope from the backend
            const data = raw.data || raw;

            // Backend returns next question or final determination
            if (data.status === 'questioning' && data.question) {
                setCurrentQuestion(data);
                setEligibilityStatus('questioning');
            } else if (data.status === 'determined') {
                setDetermination(data);
                setEligibilityStatus('determined');
            } else {
                // Fallback handling
                if (data.question) {
                    setCurrentQuestion(data);
                    setEligibilityStatus('questioning');
                } else if (data.eligible !== undefined) {
                    setDetermination(data);
                    setEligibilityStatus('determined');
                } else {
                    throw new Error('예상치 못한 응답 형식입니다.');
                }
            }

            return data;
        } catch (err) {
            setError(err.message || '답변 제출 중 오류가 발생했습니다.');
            setEligibilityStatus('error');
            return null;
        }
    }, [currentQuestion]);

    /**
     * 설명: 프로그램 혜택 접수에 가장 필요로 하는 서류 문건 가이드를 탐색하고 조회.
     * 작동 방식: POST 방식으로 program_info 등 백엔드 API 에 쿼리후 저장소에 반환값 스테이트 저장.
     * 반환값: Promise.
     * 예외: 에러 상태 로딩 반환 처리됨.
     */
    const fetchDocumentGuide = useCallback(async (programInfo, sessionId) => {
        if (!programInfo) {
            setError('프로그램 정보가 없습니다.');
            return null;
        }

        setDocumentLoading(true);
        setError(null);

        try {
            const payload = { program_info: programInfo };
            if (sessionId) {
                payload.session_id = sessionId;
            }

            const response = await fetch(DOCUMENTS_GUIDE_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`서버 오류: ${response.status}`);
            }

            const raw = await response.json();
            // Unwrap the {"status":"ok","data":{...}} envelope from the backend
            const data = raw.data || raw;
            setDocuments(data);
            setDocumentLoading(false);

            return data;
        } catch (err) {
            setError(err.message || '서류 안내 조회 중 오류가 발생했습니다.');
            setDocumentLoading(false);
            return null;
        }
    }, []);

    /**
     * 설명: 저장된 모든 자격 증명 관련 상태를 최초의 초기 대기값(idle)으로 삭제 및 회귀.
     * 작동 방식: 각 스테이트 변수들을 default 시기로 초기화.
     * 반환값: void.
     */
    const reset = useCallback(() => {
        setEligibilityStatus('idle');
        setCurrentQuestion(null);
        setDetermination(null);
        setDocuments(null);
        setQuestionHistory([]);
        setError(null);
    }, []);

    return {
        eligibilityStatus,
        currentQuestion,
        determination,
        documents,
        documentLoading,
        questionHistory,
        error,
        startCheck,
        submitAnswer,
        fetchDocumentGuide,
        reset,
    };
}

export default useEligibility;
