"""
chat_api.py

API endpoints for eligibility checking and document guide features.

Exposes five routes under the /api/v1 prefix:
  POST  /eligibility/start          — start an eligibility check
  POST  /eligibility/answer         — submit an O/X answer
  GET   /eligibility/status/{id}    — get current eligibility check state
  POST  /documents/guide            — generate a required document guide
  GET   /session/{id}               — retrieve full session info
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.logic.eligibility import get_eligibility_engine
from app.logic.document_guide import get_document_guide_engine
from app.core.session_manager import get_session_manager
from app.core.logger import logger

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class StartEligibilityRequest(BaseModel):
    """
    Description: Request body for starting an eligibility check.
    Fields:
        session_id   — active session that will hold the eligibility state
        program_info — welfare program description used to generate questions
    """
    session_id: str
    program_info: str


class AnswerRequest(BaseModel):
    """
    Description: Request body for submitting a user's answer during eligibility Q&A.
    Fields:
        session_id — session that owns the active eligibility check
        answer     — user's response: "예" or "아니오" (O/X only)
    """
    session_id: str
    answer: str  # "예" or "아니오"


class DocumentGuideRequest(BaseModel):
    """
    Description: Request body for generating a required-document guide.
    Fields:
        program_info — welfare program description used to look up documents
        session_id   — optional; when provided the eligibility result already
                       stored in the session is passed to the guide engine for
                       personalised document selection
    """
    program_info: str
    session_id: Optional[str] = None  # Optional: if provided, uses eligibility result from session


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/eligibility/start")
async def start_eligibility_check(request: StartEligibilityRequest):
    """
    Description: Starts an eligibility check for a welfare program.
    How it works: Validates the session, resets eligibility state, and calls
        the EligibilityEngine to generate the first O/X question via the LLM.
    Returns: JSON envelope {"status": "ok", "data": <first question dict>} where
        data contains keys: status, question, confidence, reason,
        remaining_questions_estimate.
    Throws: 404 if the session is not found or has expired;
            500 on unexpected engine failures.
    """
    try:
        engine = get_eligibility_engine()
        result = await engine.start_eligibility_check(
            session_id=request.session_id,
            program_info=request.program_info
        )
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Eligibility start error: {e}")
        raise HTTPException(status_code=500, detail="자격 판단 시작 중 오류가 발생했습니다.")


@router.post("/eligibility/answer")
async def submit_eligibility_answer(request: AnswerRequest):
    """
    Description: Submits an O/X answer for the current eligibility question.
    How it works: Passes the user's answer to the EligibilityEngine which
        interprets it, updates the user profile, then either generates the
        next question or delivers a final eligibility verdict.
    Returns: JSON envelope {"status": "ok", "data": <result dict>}.
        While questioning, data contains the next question. When the check is
        complete, data contains eligible (bool), confidence, and reason.
    Throws: 400 if there is no active eligibility check in the session;
            500 on unexpected engine failures.
    """
    try:
        engine = get_eligibility_engine()
        result = await engine.process_answer(
            session_id=request.session_id,
            answer=request.answer
        )
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Eligibility answer error: {e}")
        raise HTTPException(status_code=500, detail="답변 처리 중 오류가 발생했습니다.")


@router.get("/eligibility/status/{session_id}")
async def get_eligibility_status(session_id: str):
    """
    Description: Gets the current eligibility check status for a session.
    How it works: Retrieves the session from the session manager and merges
        the eligibility_state dict with profile completeness metadata. Does
        not modify any session data.
    Returns: JSON envelope {"status": "ok", "data": <status dict>} where
        data contains all eligibility_state fields plus profile_completeness
        (float 0.0–1.0) and profile (dict of collected user attributes).
    Throws: 404 if the session is not found or has expired;
            500 on unexpected errors.
    """
    try:
        engine = get_eligibility_engine()
        result = await engine.get_eligibility_status(session_id)
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Eligibility status error: {e}")
        raise HTTPException(status_code=500, detail="상태 조회 중 오류가 발생했습니다.")


@router.post("/documents/guide")
async def get_document_guide(request: DocumentGuideRequest):
    """
    Description: Generates a required-document guide for a welfare program.
    How it works:
        1. If session_id is provided, the eligibility_state from that session is
           passed to the guide engine so it can tailor the document list to the
           user's specific situation.
        2. Calls DocumentGuideEngine.generate_document_guide() which combines MCP
           real-time search, LLM analysis, and the built-in COMMON_DOCUMENTS
           database to build a structured document list with names, issuers, and
           online issuance links.
    Returns: JSON envelope {"status": "ok", "data": <guide dict>} where data
        contains program_name, documents (list), application_info, and tips.
    Throws: 500 on engine failure (the engine itself never raises, so this
        catches unexpected errors in the request handling layer).
    """
    try:
        guide_engine = get_document_guide_engine()

        # If session_id provided, get eligibility result from session
        eligibility_result = None
        if request.session_id:
            session_mgr = get_session_manager()
            session = session_mgr.get_session(request.session_id)
            if session and session.eligibility_state:
                eligibility_result = session.eligibility_state

        result = await guide_engine.generate_document_guide(
            program_info=request.program_info,
            eligibility_result=eligibility_result
        )
        return {"status": "ok", "data": result}
    except Exception as e:
        logger.error(f"Document guide error: {e}")
        raise HTTPException(status_code=500, detail="서류 안내 생성 중 오류가 발생했습니다.")


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    설명: 진행중인 세션에서 사용자가 채팅 메시지를 보낼 때 처리하여 SSE(Server-Sent Events)
        형식으로 AI의 응답을 스트리밍해 줍니다.
    작동 방식: 
        1. 세션의 존재 여부 및 유효성을 SessionManager를 통해 검증합니다.
        2. 사용자의 메시지가 빈 문자열이 아닌지 확인하고, 세션 대화 기록에 사용자 메시지를 추가합니다.
        3. LLMHandler의 stream_chat 메소드를 비동기 생성기(async generator)를 통해 호출합니다.
        4. LLM이 생성한 각 청크(chunk) 단위의 텍스트가 SSE 형태로 즉시 클라이언트로 전달됩니다.
        5. 스트리밍이 완료된 후, 완전한 AI 응답 메시지가 세션 기록에 기록됩니다.
    반환값: LLM의 응답 내용을 SSE 스트림으로 뿜어내는 StreamingResponse.
    예외: 빈 메시지일 경우 400 Bad Request 에러 발생, 세션이 없거나 
        만료된 경우에는 404 Not Found 에러 발생.
    """
    session_mgr = get_session_manager()
    session = session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    return {
        "status": "ok",
        "data": {
            "session_id": session.session_id,
            "user_profile": session.user_profile.to_dict(),
            "profile_completeness": session.user_profile.completeness_score(),
            "eligibility_state": session.eligibility_state,
            "target_programs": session.target_programs,
            "message_count": len(session.messages)
        }
    }
