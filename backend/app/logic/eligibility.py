"""
eligibility.py

Eligibility checking engine that determines user qualification for welfare
programs through a minimal series of O/X (yes/no) questions.

The engine coordinates between the LLM handler (for question generation and
answer interpretation) and the session manager (for profile persistence and
conversation history).  A maximum of MAX_QUESTIONS questions is enforced
before a forced determination is requested from the LLM.
"""

import json
from typing import Dict, Optional

from app.core.logger import logger
from app.core.session_manager import SessionData as Session, get_session_manager
from app.agents.llm_handler import get_llm_handler


# Path constants for YAML prompt templates
_ELIGIBILITY_PROMPT = "eligibility.yaml"
_FOLLOW_UP_PROMPT = "follow_up.yaml"

# Korean label map for standard UserProfile fields used in formatted output
_FIELD_LABELS: Dict[str, str] = {
    "age": "나이",
    "income_level": "소득수준",
    "region": "거주지역",
    "household_size": "가구원수",
    "employment_status": "고용상태",
    "disability_status": "장애여부",
    "veteran_status": "국가유공자여부",
}


class EligibilityEngine:
    """
    설명: 사용자가 올바른 복지 혜택 대상인지 평가, 분류하기 위한 코어 자격증명 엔진입니다.
    작동 방식: 
        1. 세션 정보를 검증하고, 초기 정보가 구축되어있다면 외부 API를 불러 자격 요건을 가져옵니다. 
        2. 대화 세션에 존재하는 유저 답변들을 기반으로 O,X 여부를 지속 묻습니다. 
        3. LLM 을 사용해 대상 조건에 충족하는지 종합적으로 검사 판별합니다.
    """

    MAX_QUESTIONS: int = 7
    MIN_CONFIDENCE: float = 0.7

    def __init__(self):
        # Description: Initializes engine with shared LLM handler and session manager singletons.
        # How it works: Retrieves the application-wide singletons so they are reused
        #     across all engine method calls without re-initializing the underlying clients.
        # Returns: None.
        self.llm = get_llm_handler()
        self.session_mgr = get_session_manager()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_eligibility_check(self, session_id: str, program_info: str) -> Dict:
        """
        설명: 자격 확인 절차(세션 초기화)를 시작하는 엔진 부팅 프로세스입니다.
        작동 방식: 
            1. session_id를 통해 세션 데이터를 로딩 및 타당성 검토.
            2. MCP Client를 활용해 프로그램의 자격 조건을 추출하고 User Profile에 등록. 
            3. 자격 조건 리스트를 성공적으로 추출했다면 LLM을 거쳐 즉시 다음 "Question"을 선별하거나 결론도출 진행.
        반환값: 다음번에 유저에게 표출하게될 상태 딕셔너리형 구문 ('status', 'data' 래핑 포함).
        예외: 세션 정보가 없거나, MCP와 LLM 등 내부 API 컴포넌트 접속에러가 났을때 
            안전한 Error dict 덤프 반환 처리됨.
        """
        session = self.session_mgr.get_session(session_id)
        if session is None:
            logger.error(f"start_eligibility_check: session {session_id!r} not found.")
            raise ValueError(f"Session '{session_id}' not found or has expired.")

        logger.info(
            f"Starting eligibility check for session {session_id}. "
            f"Program info length: {len(program_info)} chars."
        )

        # Initialize eligibility state for this check
        initial_state = {
            "status": "questioning",
            "question_count": 0,
            "program_info": program_info,
            "current_question": None,
        }
        self.session_mgr.update_eligibility_state(session_id, initial_state)

        # Record start of eligibility check in conversation history
        self.session_mgr.add_message(
            session_id,
            role="system",
            content=f"복지 프로그램 자격 확인이 시작되었습니다.\n\n[프로그램 정보]\n{program_info}",
        )

        # Generate the first question
        question_result = await self._generate_question(session)

        # Persist the current question text so process_answer can reference it
        self.session_mgr.update_eligibility_state(
            session_id, {"current_question": question_result.get("question")}
        )

        # Add the question as an assistant message
        if question_result.get("question"):
            self.session_mgr.add_message(
                session_id,
                role="assistant",
                content=question_result["question"],
            )

        logger.info(
            f"First question generated for session {session_id}. "
            f"Confidence: {question_result.get('confidence', 0):.2f}."
        )
        return question_result

    async def process_answer(self, session_id: str, answer: str) -> Dict:
        """
            8. Updates eligibility_state with the result and appends the assistant
               message if another question was generated.
        Returns: Dict with keys from the LLM response (status, question or eligible,
            confidence, reason, remaining_questions_estimate).  When status is
            "determined", eligible (bool) and reason (str) are populated.
        Throws: ValueError if the session is not found, has expired, or has no
            active eligibility check in progress.
        """
        session = self.session_mgr.get_session(session_id)
        if session is None:
            logger.error(f"process_answer: session {session_id!r} not found.")
            raise ValueError(f"Session '{session_id}' not found or has expired.")

        state = session.eligibility_state
        if state.get("status") not in ("questioning",):
            logger.warning(
                f"process_answer: session {session_id} has no active eligibility check "
                f"(status={state.get('status')!r})."
            )
            raise ValueError(
                "No active eligibility check in progress for this session. "
                "Call start_eligibility_check first."
            )

        logger.info(
            f"Processing answer for session {session_id}. "
            f"Question #{state.get('question_count', 0) + 1}."
        )

        # Record the user's answer in conversation history
        self.session_mgr.add_message(session_id, role="user", content=answer)

        # Interpret the answer and extract any profile updates
        interpretation = await self._interpret_answer(session, answer)
        logger.debug(
            f"Answer interpretation for session {session_id}: "
            f"interpreted={interpretation.get('interpreted_answer')!r}, "
            f"clarification_needed={interpretation.get('clarification_needed')}."
        )

        # Apply profile updates returned by the LLM interpreter
        profile_updates = interpretation.get("profile_update", {})
        if profile_updates:
            self.session_mgr.update_user_profile(session_id, **profile_updates)
            logger.debug(
                f"Profile updated for session {session_id}: {list(profile_updates.keys())}."
            )

        # If the answer was unclear, return a clarification question immediately
        # without consuming a question slot
        if interpretation.get("clarification_needed") and interpretation.get("clarification_question"):
            clarification_q = interpretation["clarification_question"]
            self.session_mgr.add_message(
                session_id, role="assistant", content=clarification_q
            )
            logger.info(
                f"Clarification requested for session {session_id}: {clarification_q!r}"
            )
            return {
                "status": "questioning",
                "question": clarification_q,
                "clarification": True,
                "confidence": state.get("last_confidence", 0.0),
                "reason": "사용자의 답변이 명확하지 않아 추가 확인이 필요합니다.",
                "remaining_questions_estimate": max(
                    0, self.MAX_QUESTIONS - state.get("question_count", 0)
                ),
            }

        # Increment question counter
        new_count = state.get("question_count", 0) + 1
        self.session_mgr.update_eligibility_state(
            session_id, {"question_count": new_count}
        )

        # If MAX_QUESTIONS reached, force the LLM to issue a determination
        if new_count >= self.MAX_QUESTIONS:
            logger.info(
                f"Session {session_id} reached MAX_QUESTIONS ({self.MAX_QUESTIONS}). "
                "Forcing determination."
            )
            self.session_mgr.add_message(
                session_id,
                role="system",
                content=(
                    f"[시스템] 최대 질문 횟수({self.MAX_QUESTIONS}회)에 도달했습니다. "
                    "지금까지 수집된 정보를 바탕으로 최종 자격 판정을 내려 주세요."
                ),
            )

        # Re-fetch session so the updated profile and messages are visible
        session = self.session_mgr.get_session(session_id)

        # Generate the next question or the final verdict
        result = await self._generate_question(session)

        if result.get("status") == "determined":
            # Persist final verdict into eligibility_state
            self.session_mgr.update_eligibility_state(
                session_id,
                {
                    "status": "determined",
                    "eligible": result.get("eligible"),
                    "confidence": result.get("confidence"),
                    "reason": result.get("reason"),
                },
            )
            logger.info(
                f"Eligibility determined for session {session_id}: "
                f"eligible={result.get('eligible')}, "
                f"confidence={result.get('confidence', 0):.2f}."
            )
        else:
            # Another question — persist it and add assistant message
            next_question = result.get("question")
            self.session_mgr.update_eligibility_state(
                session_id,
                {
                    "current_question": next_question,
                    "last_confidence": result.get("confidence", 0.0),
                },
            )
            if next_question:
                self.session_mgr.add_message(
                    session_id, role="assistant", content=next_question
                )
            logger.info(
                f"Next question generated for session {session_id}. "
                f"question_count={new_count}, "
                f"confidence={result.get('confidence', 0):.2f}."
            )

        return result

    async def get_eligibility_status(self, session_id: str) -> Dict:
        """
        Description: Returns a snapshot of the current eligibility check state
            together with the user profile's completeness score.
        How it works: Retrieves the session and merges eligibility_state with
            profile metadata.  Does not modify any session data.
        Returns: Dict containing all keys from eligibility_state plus
            "profile_completeness" (float 0.0–1.0) and "profile" (dict of current
            user profile fields).
        Throws: ValueError if the session is not found or has expired.
        """
        session = self.session_mgr.get_session(session_id)
        if session is None:
            logger.error(f"get_eligibility_status: session {session_id!r} not found.")
            raise ValueError(f"Session '{session_id}' not found or has expired.")

        status_dict = dict(session.eligibility_state)
        status_dict["profile_completeness"] = session.user_profile.completeness_score()
        status_dict["profile"] = session.user_profile.to_dict()
        logger.debug(
            f"Eligibility status requested for session {session_id}. "
            f"completeness={status_dict['profile_completeness']:.2f}."
        )
        return status_dict

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_question(self, session: Session) -> Dict:
        """
        Description: Calls the eligibility LLM prompt to generate the next O/X
            question or issue a final eligibility verdict.
        How it works: Formats the current user profile and conversation history
            into human-readable strings, then calls run_prompt_template with
            eligibility.yaml.  The LLM returns a JSON object that is returned
            directly to the caller.  On JSON parse failure (indicated by an "error"
            key in the response) a safe fallback dict is returned so the calling
            layer can handle the error gracefully.
        Returns: Dict with keys: status, question, question_field, question_key,
            eligible, confidence, reason, remaining_questions_estimate.
        Throws: Nothing — LLM errors are caught and returned as a fallback dict.
        """
        state = session.eligibility_state
        program_info = state.get("program_info", "")
        user_profile_str = self._format_user_profile(session)
        conversation_str = self._format_conversation(session)

        logger.debug(
            f"_generate_question called for session {session.session_id}. "
            f"question_count={state.get('question_count', 0)}."
        )

        response = await self.llm.run_prompt_template(
            prompt_file=_ELIGIBILITY_PROMPT,
            variables={
                "program_info": program_info,
                "user_profile": user_profile_str,
                "conversation_history": conversation_str,
            },
            response_format="json_object",
        )

        # Graceful handling of LLM parse failures
        if "error" in response:
            logger.error(
                f"_generate_question: LLM returned invalid JSON for session "
                f"{session.session_id}. Raw: {response.get('raw', '')[:200]}"
            )
            return {
                "status": "questioning",
                "question": "죄송합니다. 질문을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                "question_field": None,
                "question_key": None,
                "eligible": None,
                "confidence": 0.0,
                "reason": "LLM 응답 파싱 오류",
                "remaining_questions_estimate": self.MAX_QUESTIONS - state.get("question_count", 0),
            }

        return response

    async def _interpret_answer(self, session: Session, answer: str) -> Dict:
        """
        Description: Calls the follow-up LLM prompt to interpret the user's O/X
            answer and extract any structured profile data embedded in it.
        How it works: Retrieves the previous (current) question from
            eligibility_state, then calls run_prompt_template with follow_up.yaml.
            The LLM returns a JSON object with interpreted_answer ("yes"/"no"/"unclear"),
            profile_update (dict), clarification_needed (bool), and optionally a
            clarification_question string.  On JSON parse failure a safe fallback
            requesting clarification is returned.
        Returns: Dict with keys: interpreted_answer, profile_update,
            clarification_needed, clarification_question.
        Throws: Nothing — LLM errors are caught and returned as a fallback dict.
        """
        state = session.eligibility_state
        program_info = state.get("program_info", "")
        previous_question = state.get("current_question") or ""
        user_profile_str = self._format_user_profile(session)

        logger.debug(
            f"_interpret_answer called for session {session.session_id}. "
            f"answer={answer!r}."
        )

        response = await self.llm.run_prompt_template(
            prompt_file=_FOLLOW_UP_PROMPT,
            variables={
                "program_info": program_info,
                "user_profile": user_profile_str,
                "previous_question": previous_question,
                "user_answer": answer,
            },
            response_format="json_object",
        )

        # Graceful handling of LLM parse failures
        if "error" in response:
            logger.error(
                f"_interpret_answer: LLM returned invalid JSON for session "
                f"{session.session_id}. Raw: {response.get('raw', '')[:200]}"
            )
            return {
                "interpreted_answer": "unclear",
                "profile_update": {},
                "clarification_needed": True,
                "clarification_question": (
                    "답변을 이해하지 못했습니다. '예' 또는 '아니오'로 답해 주시겠어요?"
                ),
            }

        return response

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_user_profile(self, session: Session) -> str:
        """
        Description: Converts the session's UserProfile into a concise, human-readable
            Korean string suitable for injection into LLM prompts.
        How it works: Iterates over all standard fields using _FIELD_LABELS for
            Korean labels, then appends any custom_fields entries.  Fields whose
            value is None are shown as "미확인" so the LLM understands that the
            information has not yet been collected.
        Returns: Multi-line string where each line has the format "- 라벨: 값\n".
            Returns "- 수집된 정보 없음" if the profile has no data at all.
        Throws: Nothing.
        """
        profile_dict = session.user_profile.to_dict()
        lines = []

        # Standard fields with Korean labels
        for field_key, label in _FIELD_LABELS.items():
            raw_value = profile_dict.get(field_key)
            if raw_value is None:
                display_value = "미확인"
            elif isinstance(raw_value, bool):
                display_value = "예" if raw_value else "아니오"
            else:
                # Append unit suffix for common numeric fields
                if field_key == "age":
                    display_value = f"{raw_value}세"
                elif field_key == "household_size":
                    display_value = f"{raw_value}인"
                else:
                    display_value = str(raw_value)
            lines.append(f"- {label}: {display_value}")

        # Custom / extra fields (arbitrary keys from the LLM)
        custom = session.user_profile.custom_fields
        for key, value in custom.items():
            if value is None:
                display_value = "미확인"
            elif isinstance(value, bool):
                display_value = "예" if value else "아니오"
            else:
                display_value = str(value)
            lines.append(f"- {key}: {display_value}")

        if not lines:
            return "- 수집된 정보 없음"

        return "\n".join(lines)

    def _format_conversation(self, session: Session) -> str:
        """
        Description: Formats the last 10 messages of the session's conversation
            history into a compact Q/A string for LLM context injection.
        How it works: Slices the last 10 SessionMessage entries from the session's
            messages list, skips system messages (which are internal housekeeping),
            and formats assistant messages as "Q: ..." and user messages as "A: ...".
            Adjacent Q/A pairs are separated by " / " on the same line when possible,
            otherwise placed on separate lines.
        Returns: A single string of Q/A pairs separated by newlines.
            Returns "대화 내역 없음" if there are no user or assistant messages.
        Throws: Nothing.
        """
        recent = session.messages[-10:]
        parts = []
        pending_question: Optional[str] = None

        for msg in recent:
            if msg.role == "system":
                # System messages are internal — omit from conversation context
                continue
            elif msg.role == "assistant":
                # Flush any unpaired question first
                if pending_question is not None:
                    parts.append(f"Q: {pending_question}")
                pending_question = msg.content
            elif msg.role == "user":
                if pending_question is not None:
                    parts.append(f"Q: {pending_question} / A: {msg.content}")
                    pending_question = None
                else:
                    parts.append(f"A: {msg.content}")

        # Flush any trailing question that has not been answered yet
        if pending_question is not None:
            parts.append(f"Q: {pending_question}")

        return "\n".join(parts) if parts else "대화 내역 없음"


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_eligibility_engine_instance: Optional[EligibilityEngine] = None


def get_eligibility_engine() -> EligibilityEngine:
    """
    Description: Returns the application-wide singleton EligibilityEngine instance.
    How it works: Lazily instantiates EligibilityEngine on first call and caches
        it in a module-level variable.  Subsequent calls return the cached instance
        so that the underlying LLM client and session manager singletons are shared
        without re-initialization overhead.
    Returns: The singleton EligibilityEngine instance.
    Throws: Nothing.
    """
    global _eligibility_engine_instance
    if _eligibility_engine_instance is None:
        _eligibility_engine_instance = EligibilityEngine()
        logger.info("EligibilityEngine singleton created.")
    return _eligibility_engine_instance
