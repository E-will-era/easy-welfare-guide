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
import re
from datetime import datetime, date
from typing import Dict, Optional

from app.core.logger import logger
from app.core.session_manager import SessionData as Session, get_session_manager
from app.agents.llm_handler import get_llm_handler
from app.mcp.search_client import get_mcp_client


# Path constants for YAML prompt templates
_QUESTIONS_PROMPT = "eligibility_questions.yaml"
_DETERMINE_PROMPT = "eligibility_determine.yaml"

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
    MAX_QUESTIONS: int = 7
    MIN_CONFIDENCE: float = 0.7

    def __init__(self):
        self.llm = get_llm_handler()
        self.session_mgr = get_session_manager()
        self.mcp_client = get_mcp_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_eligibility_check(self, session_id: str, program_info: str) -> Dict:
        session = self.session_mgr.get_session(session_id)
        if session is None:
            logger.error(f"start_eligibility_check: session {session_id!r} not found.")
            raise ValueError(f"Session '{session_id}' not found or has expired.")

        logger.info(
            f"Starting eligibility check for session {session_id}. "
            f"Program info length: {len(program_info)} chars."
        )

        # MCP를 통해 정부 포털에서 자격 조건 보완 검색
        enriched_info = await self._enrich_with_mcp(program_info)

        # 신청 기한 만료 여부 사전 체크
        expired_reason = self._check_program_expired(enriched_info)
        if expired_reason:
            logger.info(
                f"Program expired for session {session_id}: {expired_reason}"
            )
            expired_state = {
                "status": "determined",
                "question_count": 0,
                "program_info": enriched_info,
                "current_question": None,
                "question_queue": [],
                "eligible": False,
                "confidence": 1.0,
                "reason": expired_reason,
            }
            self.session_mgr.update_eligibility_state(session_id, expired_state)
            return {
                "status": "determined",
                "question": None,
                "eligible": False,
                "confidence": 1.0,
                "reason": expired_reason,
                "remaining_questions_estimate": 0,
            }

        # Initialize eligibility state
        initial_state = {
            "status": "questioning",
            "question_count": 0,
            "program_info": enriched_info,
            "current_question": None,
            "question_queue": [],
        }
        self.session_mgr.update_eligibility_state(session_id, initial_state)

        # Record start of eligibility check in conversation history
        self.session_mgr.add_message(
            session_id,
            role="system",
            content=f"복지 프로그램 자격 확인이 시작되었습니다.\n\n[프로그램 정보]\n{enriched_info}",
        )

        # Re-fetch session
        session = self.session_mgr.get_session(session_id)

        # Generate all questions initially
        questions = await self._generate_questions_queue(session)

        if not questions:
            logger.warning(f"Failed to generate question queue for session {session_id}, determining immediately.")
            return await self._run_determination(session_id)

        # Pop first question
        first_q = questions.pop(0)
        q_text = first_q.get("question", "질문이 없습니다.")

        self.session_mgr.update_eligibility_state(
            session_id,
            {
                "current_question": q_text,
                "current_question_meta": {
                    "field": first_q.get("field", "custom"),
                    "key": first_q.get("key"),
                },
                "question_queue": questions,
                "question_count": 1,
            }
        )

        if q_text:
            self.session_mgr.add_message(session_id, role="assistant", content=q_text)

        logger.info(f"First question generated for session {session_id}.")
        return {
            "status": "questioning",
            "question": q_text,
            "confidence": 0.0,
            "reason": None,
            "remaining_questions_estimate": len(questions)
        }

    async def process_answer(self, session_id: str, answer: str) -> Dict:
        session = self.session_mgr.get_session(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found or has expired.")

        state = session.eligibility_state
        if state.get("status") not in ("questioning",):
            raise ValueError("No active eligibility check in progress for this session. Call start_eligibility_check first.")

        logger.info(f"Processing answer for session {session_id}. Question #{state.get('question_count', 0)}.")

        # Record the user's answer
        self.session_mgr.add_message(session_id, role="user", content=answer)

        # Interpret the answer (rule-based, no LLM call)
        interpretation = self._interpret_answer(session, answer)
        logger.debug(f"Answer interpretation: {interpretation.get('interpreted_answer')!r}")

        profile_updates = interpretation.get("profile_update", {})
        if profile_updates:
            self.session_mgr.update_user_profile(session_id, **profile_updates)
            logger.debug(f"Profile updated: {list(profile_updates.keys())}.")

        questions_queue = state.get("question_queue", [])
        new_count = state.get("question_count", 0) + 1
        
        if not questions_queue or new_count >= self.MAX_QUESTIONS:
            logger.info(f"Session {session_id} queue empty or MAX_QUESTIONS reached. Forcing determination.")
            return await self._run_determination(session_id)

        next_q = questions_queue.pop(0)
        q_text = next_q.get("question", "질문이 없습니다.")

        self.session_mgr.update_eligibility_state(
            session_id,
            {
                "current_question": q_text,
                "current_question_meta": {
                    "field": next_q.get("field", "custom"),
                    "key": next_q.get("key"),
                },
                "question_queue": questions_queue,
                "question_count": new_count,
            }
        )

        if q_text:
            self.session_mgr.add_message(session_id, role="assistant", content=q_text)

        logger.info(f"Next question popped for session {session_id}.")
        return {
            "status": "questioning",
            "question": q_text,
            "confidence": 0.0,
            "reason": None,
            "remaining_questions_estimate": len(questions_queue)
        }

    async def get_eligibility_status(self, session_id: str) -> Dict:
        session = self.session_mgr.get_session(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found or has expired.")

        status_dict = dict(session.eligibility_state)
        status_dict["profile_completeness"] = session.user_profile.completeness_score()
        status_dict["profile"] = session.user_profile.to_dict()
        return status_dict

    # ------------------------------------------------------------------
    # Pre-check helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_program_expired(program_info: str) -> Optional[str]:
        today = date.today()
        current_year = today.year

        # 년도 기준 만료 패턴 (과거 연도 + "기준")
        past_year_pattern = re.compile(r'(20\d{2})년\s*기준', re.UNICODE)
        match = past_year_pattern.search(program_info)
        if match:
            year = int(match.group(1))
            if year < current_year:
                return f"과거({year}년) 기준의 프로그램으로 현재는 신청 기간이 만료되었습니다."

        # 명시적 만료 텍스트 패턴
        text_patterns = [
            "기간 지난 공고", "신청기간이 종료되었습니다", "신청 기간 종료",
            "마감되었습니다", "1차 신청기간 종료"
        ]
        for p in text_patterns:
            if p in program_info:
                return "신청 기한이 종료된 프로그램입니다."

        # 연월일 패턴 (4자리 연도 필수)
        full_date_pattern = r'(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})[일.]?'
        # 연도 없는 월일 패턴 (시작 날짜에서 연도를 상속)
        short_date_pattern = r'(\d{1,2})[.\-/월]\s*(\d{1,2})[일.]?'

        def parse_full_date(m, g_offset=1):
            try:
                y = int(m.group(g_offset))
                mo = int(m.group(g_offset + 1))
                d = int(m.group(g_offset + 2))
                return date(y, mo, d)
            except (ValueError, OverflowError):
                return None

        # 범위 패턴 1: 시작/끝 모두 연도 있는 경우
        range_full = re.compile(
            r'(?:신청기한|접수기간|모집기간|신청기간|사업기간)?'
            r'[^0-9]{0,15}'
            + full_date_pattern
            + r'[\s.:]*(?:\d{1,2}:\d{2})?\s*[~∼\-]\s*'
            + full_date_pattern,
            re.UNICODE,
        )
        for m in range_full.finditer(program_info):
            end_date = parse_full_date(m, g_offset=4)
            if end_date and end_date < today:
                return f"신청 기한이 종료된 프로그램입니다. (마감일: {end_date.year}년 {end_date.month}월 {end_date.day}일)"

        # 범위 패턴 2: 시작에만 연도, 끝은 월.일만 있는 경우
        # 예: 2024. 6. 1. 00:00 ~ 6. 11. 18:00
        range_short_end = re.compile(
            r'(?:신청기한|접수기간|모집기간|신청기간|사업기간)?'
            r'[^0-9]{0,15}'
            + full_date_pattern
            + r'[\s.:]*(?:\d{1,2}:\d{2})?\s*[~∼\-]\s*'
            + short_date_pattern,
            re.UNICODE,
        )
        for m in range_short_end.finditer(program_info):
            start_date = parse_full_date(m, g_offset=1)
            if not start_date:
                continue
            try:
                end_month = int(m.group(4))
                end_day = int(m.group(5))
                # 끝 월이 시작 월보다 작으면 다음 해로 추정
                end_year = start_date.year
                if end_month < start_date.month:
                    end_year += 1
                end_date = date(end_year, end_month, end_day)
                if end_date < today:
                    return f"신청 기한이 종료된 프로그램입니다. (마감일: {end_date.year}년 {end_date.month}월 {end_date.day}일)"
            except (ValueError, OverflowError):
                continue

        # 마감/종료 + 날짜 패턴
        deadline_pattern = re.compile(
            r'(?:마감|종료|까지|신청기한|접수마감)'
            r'[^0-9]{0,20}'
            + full_date_pattern,
            re.UNICODE,
        )
        for m in deadline_pattern.finditer(program_info):
            d = parse_full_date(m)
            if d and d < today:
                return f"신청 기한이 종료된 프로그램입니다. (마감일: {d.year}년 {d.month}월 {d.day}일)"

        # 날짜 + 마감/종료 패턴
        reverse_pattern = re.compile(
            full_date_pattern + r'[^0-9]{0,10}(?:마감|종료|까지)',
            re.UNICODE,
        )
        for m in reverse_pattern.finditer(program_info):
            d = parse_full_date(m)
            if d and d < today:
                return f"신청 기한이 종료된 프로그램입니다. (마감일: {d.year}년 {d.month}월 {d.day}일)"

        return None

    # ------------------------------------------------------------------
    # MCP helpers
    # ------------------------------------------------------------------

    async def _enrich_with_mcp(self, program_info: str) -> str:
        # Markdown 제거: 헤더, 볼드, 이탤릭, 리스트 마커 등 제거하여 검색에 최적화
        clean_name = re.sub(r'#+\s*', '', program_info)
        clean_name = re.sub(r'\*\*|__|\*|_', '', clean_name)
        clean_name = re.sub(r'^[\s\-*+]+', '', clean_name, flags=re.MULTILINE)
        
        # 첫 번째 유의미한 줄 추출
        lines = [L.strip() for L in clean_name.split('\n') if L.strip()]
        if lines:
            program_name = lines[0][:80].strip()
        else:
            program_name = clean_name[:80].strip()

        logger.info(f"_enrich_with_mcp: searching eligibility for '{program_name}'")

        try:
            mcp_result = await self.mcp_client.search_eligibility(
                program_name=program_name,
                user_info={},
            )
        except Exception as exc:
            logger.warning(f"_enrich_with_mcp: MCP search failed: {exc}")
            return program_info

        criteria = mcp_result.get("criteria", [])
        source_url = mcp_result.get("source_url", "")

        if not criteria:
            logger.info("_enrich_with_mcp: MCP returned no additional criteria.")
            return program_info

        mcp_section = "\n\n[정부 포털 참조 자격 조건]\n"
        mcp_section += "\n".join(f"- {c}" for c in criteria)
        if source_url:
            mcp_section += f"\n(출처: {source_url})"

        enriched = program_info + mcp_section
        logger.info(f"_enrich_with_mcp: enriched program_info with {len(criteria)} criteria from MCP.")
        return enriched

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    async def _generate_questions_queue(self, session: Session) -> list:
        state = session.eligibility_state
        program_info = state.get("program_info", "")

        logger.debug(f"_generate_questions_queue called for session {session.session_id}.")

        response = await self.llm.run_prompt_template(
            prompt_file=_QUESTIONS_PROMPT,
            variables={"program_info": program_info},
            response_format="json_object",
        )

        if "error" in response:
            logger.error(
                f"_generate_questions_queue: LLM returned invalid JSON for session "
                f"{session.session_id}. Raw: {response.get('raw', '')[:200]}"
            )
            return []

        return response.get("questions", [])

    async def _run_determination(self, session_id: str) -> Dict:
        self.session_mgr.add_message(
            session_id,
            role="system",
            content="[시스템] 대답 정보를 바탕으로 최종 자격 판정을 시도합니다."
        )
        
        session = self.session_mgr.get_session(session_id)
        result = await self._determine_eligibility(session)
        
        self.session_mgr.update_eligibility_state(
            session_id,
            {
                "status": "determined",
                "eligible": result.get("eligible"),
                "confidence": result.get("confidence"),
                "reason": result.get("reason"),
            }
        )
        
        return {
            "status": "determined",
            "eligible": result.get("eligible"),
            "confidence": result.get("confidence"),
            "reason": result.get("reason"),
            "remaining_questions_estimate": 0
        }

    async def _determine_eligibility(self, session: Session) -> Dict:
        state = session.eligibility_state
        program_info = state.get("program_info", "")
        user_profile_str = self._format_user_profile(session)
        conversation_str = self._format_conversation(session)

        logger.debug(f"_determine_eligibility called for session {session.session_id}.")

        response = await self.llm.run_prompt_template(
            prompt_file=_DETERMINE_PROMPT,
            variables={
                "program_info": program_info,
                "user_profile": user_profile_str,
                "conversation_history": conversation_str,
            },
            response_format="json_object",
        )

        if "error" in response:
            logger.error(
                f"_determine_eligibility: LLM returned invalid JSON for session "
                f"{session.session_id}. Raw: {response.get('raw', '')[:200]}"
            )
            return {
                "status": "determined",
                "eligible": False,
                "confidence": 0.0,
                "reason": "최종 자격 판정 파싱 중 오류가 발생했습니다."
            }

        response["status"] = "determined"
        return self._normalize_eligibility_response(response)

    @staticmethod
    def _normalize_eligibility_response(response: Dict) -> Dict:
        raw_eligible = response.get("eligible")
        if isinstance(raw_eligible, str):
            response["eligible"] = raw_eligible.lower() == "true"
        elif raw_eligible is None:
            response["eligible"] = None

        raw_confidence = response.get("confidence")
        if isinstance(raw_confidence, str):
            try:
                response["confidence"] = float(raw_confidence)
            except ValueError:
                response["confidence"] = 0.0
        elif raw_confidence is None:
            response["confidence"] = 0.0

        if response.get("status") == "determined" and response["eligible"] is not None:
            reason = response.get("reason", "")
            negative_indicators = [
                "충족하지 못", "충족하지 않", "해당하지 않", "해당되지 않",
                "자격이 없", "자격 없", "대상이 아닌", "대상이 아님",
                "불가능", "부적합", "미충족", "미달",
            ]
            positive_indicators = [
                "충족합니다", "충족하는 것으로", "자격을 갖추",
                "자격이 있", "자격 있", "해당합니다", "해당되는 것으로",
                "대상입니다", "대상으로 확인",
            ]

            reason_suggests_ineligible = any(kw in reason for kw in negative_indicators)
            reason_suggests_eligible = any(kw in reason for kw in positive_indicators)

            if response["eligible"] is True and reason_suggests_ineligible and not reason_suggests_eligible:
                logger.warning(
                    f"Eligibility inconsistency detected: eligible=True but reason "
                    f"suggests ineligible. Correcting to eligible=False. "
                    f"Reason: {reason[:100]}"
                )
                response["eligible"] = False
            elif response["eligible"] is False and reason_suggests_eligible and not reason_suggests_ineligible:
                logger.warning(
                    f"Eligibility inconsistency detected: eligible=False but reason "
                    f"suggests eligible. Correcting to eligible=True. "
                    f"Reason: {reason[:100]}"
                )
                response["eligible"] = True

        return response

    # ------------------------------------------------------------------
    # Rule-based answer interpretation (no LLM call)
    # ------------------------------------------------------------------

    _YES_ANSWERS = {"예", "o"}
    _NO_ANSWERS = {"아니오", "x"}

    def _interpret_answer(self, session: Session, answer: str) -> Dict:
        """O/X 답변만 처리. 프론트엔드에서 '예' 또는 '아니오'만 전송됩니다."""
        state = session.eligibility_state
        normalized = answer.strip().lower()
        current_q_meta = state.get("current_question_meta", {})
        field = current_q_meta.get("field", "custom")
        key = current_q_meta.get("key")

        if normalized in self._YES_ANSWERS:
            is_yes = True
        elif normalized in self._NO_ANSWERS:
            is_yes = False
        else:
            is_yes = True if normalized in {"네", "yes", "y", "ㅇ"} else False

        profile_update = self._build_profile_update(field, key, is_yes)

        return {
            "interpreted_answer": "yes" if is_yes else "no",
            "profile_update": profile_update,
            "clarification_needed": False,
            "clarification_question": None,
        }

    @staticmethod
    def _build_profile_update(field: str, key: Optional[str], is_yes: bool) -> Dict:
        """field 메타데이터와 O/X 결과를 기반으로 프로필 업데이트 딕셔너리를 생성합니다."""
        update: Dict = {}

        if field == "income_level":
            update["income_level"] = "low" if is_yes else "medium"
        elif field == "employment_status":
            update["employment_status"] = "employed" if is_yes else "unemployed"
        elif field == "disability_status":
            update["disability_status"] = is_yes
        elif field == "veteran_status":
            update["veteran_status"] = is_yes
        elif field == "custom" and key:
            update[key] = is_yes

        return update

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_user_profile(self, session: Session) -> str:
        profile_dict = session.user_profile.to_dict()
        lines = []

        for field_key, label in _FIELD_LABELS.items():
            raw_value = profile_dict.get(field_key)
            if raw_value is None:
                display_value = "미확인"
            elif isinstance(raw_value, bool):
                display_value = "예" if raw_value else "아니오"
            else:
                if field_key == "age":
                    display_value = f"{raw_value}세"
                elif field_key == "household_size":
                    display_value = f"{raw_value}인"
                else:
                    display_value = str(raw_value)
            lines.append(f"- {label}: {display_value}")

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
        recent = session.messages[-10:]
        parts = []
        pending_question: Optional[str] = None

        for msg in recent:
            if msg.role == "system":
                continue
            elif msg.role == "assistant":
                if pending_question is not None:
                    parts.append(f"Q: {pending_question}")
                pending_question = msg.content
            elif msg.role == "user":
                if pending_question is not None:
                    parts.append(f"Q: {pending_question} / A: {msg.content}")
                    pending_question = None
                else:
                    parts.append(f"A: {msg.content}")

        if pending_question is not None:
            parts.append(f"Q: {pending_question}")

        return "\n".join(parts) if parts else "대화 내역 없음"


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_eligibility_engine_instance: Optional[EligibilityEngine] = None


def get_eligibility_engine() -> EligibilityEngine:
    global _eligibility_engine_instance
    if _eligibility_engine_instance is None:
        _eligibility_engine_instance = EligibilityEngine()
        logger.info("EligibilityEngine singleton created.")
    return _eligibility_engine_instance
