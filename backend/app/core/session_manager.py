"""
session_manager.py

Server-side session memory manager for multi-turn eligibility checking interactions.
Stores conversation history, user profiles, and eligibility check state per session.

NOTE: The singleton instance's cleanup task must be started during application
initialization. Example in your FastAPI lifespan or startup event:

    from app.core.session_manager import get_session_manager

    @app.on_event("startup")
    async def startup():
        get_session_manager().start_cleanup()

The cleanup loop is an asyncio task and requires an active event loop at call time.
"""

import asyncio
import uuid
import time
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from app.core.logger import logger


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UserProfile:
    """
    Description: Stores extracted user information gathered during eligibility checks.
    Fields cover the most common welfare eligibility criteria. Arbitrary extra
    fields are stored in custom_fields for extensibility.
    """

    age: Optional[int] = None
    income_level: Optional[str] = None      # "low", "medium", "high"
    region: Optional[str] = None
    household_size: Optional[int] = None
    employment_status: Optional[str] = None
    disability_status: Optional[bool] = None
    veteran_status: Optional[bool] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """
        Description: Serializes the profile to a plain dictionary.
        How it works: Converts all dataclass fields plus custom_fields into a
            flat dict suitable for JSON serialisation or LLM context injection.
        Returns: Dict containing all profile fields.
        Throws: Nothing.
        """
        return {
            "age": self.age,
            "income_level": self.income_level,
            "region": self.region,
            "household_size": self.household_size,
            "employment_status": self.employment_status,
            "disability_status": self.disability_status,
            "veteran_status": self.veteran_status,
            **self.custom_fields,
        }

    def completeness_score(self) -> float:
        """
        Description: Returns a score between 0.0 and 1.0 indicating how complete
            the core profile fields are.
        How it works: Counts the number of non-None values among the seven fixed
            core fields and divides by seven. custom_fields are not counted so
            that optional extra data does not inflate the score.
        Returns: float in [0.0, 1.0].
        Throws: Nothing.
        """
        core_fields = [
            self.age,
            self.income_level,
            self.region,
            self.household_size,
            self.employment_status,
            self.disability_status,
            self.veteran_status,
        ]
        filled = sum(1 for v in core_fields if v is not None)
        return filled / len(core_fields)


@dataclass
class SessionMessage:
    """
    Description: Represents a single message in a session's conversation history.
    """

    role: str                       # "system", "assistant", "user"
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionData:
    """
    설명: 단일 사용자 세션과 이와 관련된 모든 맥락, 식별자, 기록 상태를 보관하는 데이터 컨테이너.
    필드:
        session_id    - UUID4 형태로 발급된 세션의 고유 식별 지정자 문자열.
        created_at    - 세션이 최초 생성된 시간을 기록하는 타임스탬프 (UTC).
        last_accessed - 세션이 마지막으로 호출 조회 되거나 업데이트 된 타임스탬프.
        chat_history  - Chat-role 과 그 내용으로 쌓여지는 배열 리스트 (Dict List).
        user_profile  - 자격 증명 (Eligibility) 체크 및 엔진 가동에 있어서 유저의 선택 데이터, 상태등이 기록.
    """

    session_id: str
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    messages: List[SessionMessage] = field(default_factory=list)
    user_profile: UserProfile = field(default_factory=UserProfile)
    eligibility_state: Dict[str, Any] = field(default_factory=dict)
    # Welfare programs being evaluated in this session
    target_programs: List[str] = field(default_factory=list)
    # Results stored from the main RAG / analysis pipeline
    analysis_context: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, ttl_seconds: int = 1800) -> bool:
        """
        Description: Checks whether the session has been inactive for longer than
            the given TTL.
        How it works: Compares the current wall-clock time against last_accessed.
            If the difference exceeds ttl_seconds the session is considered stale.
        Returns: True if the session is expired, False otherwise.
        Throws: Nothing.
        """
        return (time.time() - self.last_accessed) > ttl_seconds

    def touch(self):
        """
        Description: Refreshes the session's last_accessed timestamp to prevent
            premature expiry while the user is actively conversing.
        How it works: Overwrites last_accessed with the current wall-clock time.
        Returns: None.
        Throws: Nothing.
        """
        self.last_accessed = time.time()


# ---------------------------------------------------------------------------
# Session manager
# ---------------------------------------------------------------------------

class SessionManager:
    """
    Description: Manages user sessions with in-memory storage and automatic cleanup.
    How it works: Stores Session objects in a dict keyed by session_id (UUID4
        string). A background asyncio task runs every cleanup_interval seconds to
        evict sessions that have exceeded their TTL. Provides CRUD operations for
        sessions as well as convenience helpers for conversation and profile
        management. A hard limit of MAX_SESSIONS concurrent sessions is enforced
        to cap memory usage.
    """

    MAX_SESSIONS: int = 1000

    def __init__(self, ttl_seconds: int = 1800, cleanup_interval: int = 300):
        """
        Description: Initialises the session manager.
        How it works: Sets configuration parameters and creates the in-memory
            storage dict and counters. Does NOT start the background cleanup task
            — call start_cleanup() from the application startup event.
        Returns: None.
        Throws: Nothing.
        """
        self._ttl_seconds: int = ttl_seconds
        self._cleanup_interval: int = cleanup_interval
        self._sessions: Dict[str, SessionData] = {}
        self._total_created: int = 0
        self._cleanup_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Session CRUD
    # ------------------------------------------------------------------

    def create_session(self) -> str:
        """
        설명: 새로운 신규 세션을 창조하고 고유의 식별 id값을 리턴합니다.
        작동 방식: 임의의 UUID 토큰 아이디를 만들어 내부 딕셔너리에 SessionData 형태로 씌워 
            등록 기록시킨 뒤 아이디 문자열을 배출해냅니다.
        반환값: String 문자열 형태의 세션 UUID 값.
        """
        if len(self._sessions) >= self.MAX_SESSIONS:
            raise RuntimeError(
                f"Session limit reached ({self.MAX_SESSIONS}). "
                "Cannot create new session."
            )

        session_id = str(uuid.uuid4())
        session = SessionData(session_id=session_id)
        self._sessions[session_id] = session
        self._total_created += 1
        logger.debug(f"Created session {session_id}. Active sessions: {len(self._sessions)}")
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        설명: session_id 값을 기준으로 등록되어있는 살아있는 세션을 반환시킵니다.
        작동 방식: 아이디를 딕셔너리 안에서 서치합니다. 만약 검색되면 last_accessed 속성을 
            지금 현재 시간 기준으로 최신화 하여 타이머 생명을 연장한 뒤 객체를 넘겨줍니다.
        반환값: 발견될경우 SessionData 요소 반환, 없을경우 None 리턴.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None

        if session.is_expired(self._ttl_seconds):
            logger.debug(f"Session {session_id} has expired — removing.")
            del self._sessions[session_id]
            return None

        session.touch()
        return session

    def delete_session(self, session_id: str) -> bool:
        """
        설명: 명시적으로 특정 세션을 서버 메모리에서 영구 삭제 처리합니다.
        반환값: 기존 매모리에 존재하여 정상적으로 지워졌으면 True, 애초에 없었으면 False.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"Deleted session {session_id}.")
            return True
        return False

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict = None,
    ) -> bool:
        """
        Description: Appends a message to the conversation history of a session.
        How it works: Resolves the session via get_session (which also refreshes
            last_accessed). Creates a SessionMessage dataclass and appends it to
            the session's messages list.
        Returns: True if the message was added successfully, False if the session
            was not found or had expired.
        Throws: Nothing.
        """
        session = self.get_session(session_id)
        if session is None:
            logger.warning(f"add_message: session {session_id} not found.")
            return False

        message = SessionMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        session.messages.append(message)
        logger.debug(
            f"Added {role!r} message to session {session_id}. "
            f"Total messages: {len(session.messages)}"
        )
        return True

    def get_conversation_context(
        self,
        session_id: str,
        max_messages: int = 20,
    ) -> List[Dict]:
        """
        Description: Returns recent conversation history formatted as a list of
            role/content dicts ready to be passed directly to an LLM API.
        How it works: Retrieves the session, takes the last max_messages entries
            from the messages list (preserving chronological order), and converts
            each SessionMessage into a minimal {"role": ..., "content": ...} dict.
        Returns: List of dicts with keys "role" and "content". Empty list if the
            session is not found.
        Throws: Nothing.
        """
        session = self.get_session(session_id)
        if session is None:
            logger.warning(f"get_conversation_context: session {session_id} not found.")
            return []

        recent = session.messages[-max_messages:]
        return [{"role": msg.role, "content": msg.content} for msg in recent]

    # ------------------------------------------------------------------
    # User profile
    # ------------------------------------------------------------------

    def update_user_profile(self, session_id: str, **kwargs) -> bool:
        """
        Description: Updates one or more fields of the session's UserProfile.
        How it works: Retrieves the session, then iterates over the provided
            keyword arguments. Known UserProfile attributes (age, income_level,
            region, household_size, employment_status, disability_status,
            veteran_status) are set directly on the dataclass. Unknown keys are
            stored inside custom_fields for extensibility.
        Returns: True if the profile was updated, False if the session was not found.
        Throws: Nothing.
        """
        session = self.get_session(session_id)
        if session is None:
            logger.warning(f"update_user_profile: session {session_id} not found.")
            return False

        known_fields = {
            "age",
            "income_level",
            "region",
            "household_size",
            "employment_status",
            "disability_status",
            "veteran_status",
        }

        for key, value in kwargs.items():
            if key in known_fields:
                setattr(session.user_profile, key, value)
            else:
                session.user_profile.custom_fields[key] = value

        logger.debug(
            f"Updated user profile for session {session_id}. "
            f"Completeness: {session.user_profile.completeness_score():.2f}"
        )
        return True

    # ------------------------------------------------------------------
    # Eligibility state
    # ------------------------------------------------------------------

    def update_eligibility_state(self, session_id: str, state: Dict) -> bool:
        """
        Description: Merges new eligibility check state into the session's
            existing eligibility_state dict.
        How it works: Retrieves the session, then calls dict.update() with the
            provided state dict so that existing keys are overwritten and new keys
            are added. This allows incremental updates as the Q&A progresses.
        Returns: True if updated successfully, False if the session was not found.
        Throws: Nothing.
        """
        session = self.get_session(session_id)
        if session is None:
            logger.warning(f"update_eligibility_state: session {session_id} not found.")
            return False

        session.eligibility_state.update(state)
        logger.debug(f"Updated eligibility state for session {session_id}.")
        return True

    # ------------------------------------------------------------------
    # Analysis context
    # ------------------------------------------------------------------

    def store_analysis_context(self, session_id: str, context: Dict) -> bool:
        """
        Description: Stores the main pipeline analysis results inside the session
            for later use during eligibility Q&A.
        How it works: Retrieves the session, then replaces (or merges) its
            analysis_context dict with the provided context dict using dict.update().
            Typical keys include admin_summary, plain_summary, and references from
            the RAG pipeline.
        Returns: True if stored successfully, False if the session was not found.
        Throws: Nothing.
        """
        session = self.get_session(session_id)
        if session is None:
            logger.warning(f"store_analysis_context: session {session_id} not found.")
            return False

        session.analysis_context.update(context)
        logger.debug(f"Stored analysis context for session {session_id}.")
        return True

    # ------------------------------------------------------------------
    # Background cleanup
    # ------------------------------------------------------------------

    async def _cleanup_loop(self):
        """
        Description: Background coroutine that periodically evicts expired sessions.
        How it works: Sleeps for cleanup_interval seconds, then iterates over a
            snapshot of the sessions dict keys. For each key it checks whether the
            session has exceeded the TTL; if so the session is deleted. The loop
            runs indefinitely until the asyncio task is cancelled (e.g. on
            application shutdown). Statistics are logged after each cleanup pass.
        Returns: None (runs until cancelled).
        Throws: asyncio.CancelledError is caught silently to allow clean shutdown.
        """
        logger.info(
            f"Session cleanup loop started "
            f"(TTL={self._ttl_seconds}s, interval={self._cleanup_interval}s)."
        )
        try:
            while True:
                await asyncio.sleep(self._cleanup_interval)

                expired_ids = [
                    sid
                    for sid, session in list(self._sessions.items())
                    if session.is_expired(self._ttl_seconds)
                ]

                for sid in expired_ids:
                    self._sessions.pop(sid, None)

                if expired_ids:
                    logger.info(
                        f"Session cleanup: removed {len(expired_ids)} expired session(s). "
                        f"Active sessions remaining: {len(self._sessions)}"
                    )
                else:
                    logger.debug(
                        f"Session cleanup: no expired sessions. "
                        f"Active: {len(self._sessions)}"
                    )

        except asyncio.CancelledError:
            logger.info("Session cleanup loop stopped.")

    def start_cleanup(self) -> None:
        """
        설명: 백그라운드 환경 상에서 유통기한이 지난 만료 세션들을 비우는 정리 태스크 런처.
        작동 방식: 현재 띄워져 있는 메인 이벤트 루프에 비동기 루프 태스크를 추가 전송합니다.
        반환값: 없음. (None)
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            logger.warning("Cleanup task already running — restarting.")
            self._cleanup_task.cancel()

        self._cleanup_task = asyncio.ensure_future(self._cleanup_loop())
        logger.info("Session cleanup background task scheduled.")

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """
        Description: Returns runtime statistics for the session manager.
        How it works: Counts active (non-expired) sessions by iterating the
            internal dict without modifying it. Estimates memory usage by
            multiplying the active session count by an empirical per-session
            average size of ~5 KB.
        Returns: Dict with keys:
            - active_sessions (int): number of live sessions currently stored
            - total_created (int): cumulative sessions created since startup
            - memory_estimate_mb (float): rough memory consumption estimate in MB
        Throws: Nothing.
        """
        active = len(self._sessions)
        # Rough estimate: ~5 KB per session (history + profile overhead)
        memory_estimate_mb = (active * 5 * 1024) / (1024 * 1024)
        return {
            "active_sessions": active,
            "total_created": self._total_created,
            "memory_estimate_mb": round(memory_estimate_mb, 4),
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_session_manager_instance: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Description: Returns the application-wide singleton SessionManager instance.
    How it works: On the first call the instance is created with default TTL and
        cleanup interval values. Subsequent calls return the cached instance.
        Thread-safety note: in a single-threaded asyncio application (standard
        FastAPI deployment) this is safe. If the application uses multiple OS
        threads sharing the same Python interpreter, callers should initialise
        the singleton at import time before spawning threads.
    Returns: The singleton SessionManager instance.
    Throws: Nothing.
    """
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
        logger.info("SessionManager singleton created.")
    return _session_manager_instance
