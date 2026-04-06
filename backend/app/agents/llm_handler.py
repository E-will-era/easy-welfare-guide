import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from openai import AsyncOpenAI, RateLimitError
from app.core.config import settings
from app.agents.human import PromptLoader

logger = logging.getLogger(__name__)

# 429 Rate Limit 재시도 설정
_MAX_RETRIES = 6
_BASE_BACKOFF = 5.0  # 초 단위 (5s → 10s → 20s → 40s → 80s → 160s 지수 백오프)

# 연속 호출 간 최소 간격 (초)
_MIN_CALL_INTERVAL = 5.0


class LLMHandler:
    # 설명: OpenAI 호환 API 엔드포인트를 통해 모든 LLM 상호작용을 처리합니다.
    # 작동 방식: 구성 가능한 base_url(예: vLLM 서버)을 가리키는 AsyncOpenAI 클라이언트를
    #            초기화하고, YAML 프롬프트를 로드하여 변수를 대체하고 모델을 호출하는
    #            단일 run_prompt_template 메서드를 제공합니다.
    # 반환값: 비동기 사용 준비가 된 LLMHandler 인스턴스

    def __init__(self):
        # 설명: LLM 클라이언트와 프롬프트 로더를 초기화합니다.
        # 작동 방식: 일반적인 LLM_API_KEY와 LLM_BASE_URL 설정을 사용하여 AsyncOpenAI 클라이언트를
        #            생성하며, vLLM이 제공하는 EXAONE 모델을 포함하여 모든
        #            OpenAI 호환 엔드포인트와 호환되도록 합니다.
        # 반환값: 없음
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=120.0,  # 2분 타임아웃
        )
        self.prompt_loader = PromptLoader()
        self._last_call_time = 0.0

    async def run_prompt_template(
        self,
        prompt_file: str,
        variables: Dict[str, str] = {},
        response_format: str = "text",
        image_url: Optional[str] = None
    ) -> Any:
        # 설명: 구성된 LLM에 대해 YAML 기반 프롬프트 템플릿을 실행합니다.
        # 작동 방식:
        #   1. PromptLoader를 통해 YAML 프롬프트 파일을 로드합니다.
        #   2. 제공된 변수를 템플릿 문자열에 대체합니다.
        #   3. EXAONE(및 일반 vLLM 엔드포인트)는 비전 입력을 지원하지 않으므로,
        #      image_url이 제공되면 즉시 ValueError를 발생시킵니다.
        #   4. 시스템 메시지를 포함하여 표준 채팅 완성 요청을 작성합니다.
        #   5. 선택적으로 json_object 응답 형식을 요청합니다.
        #   6. 모델을 호출하고 파싱된 JSON 또는 공백이 제거된 텍스트를 반환합니다.
        # 반환값: response_format이 "json_object"인 경우 파싱된 dict, 그렇지 않으면 str.
        # 예외:
        #   ValueError: image_url이 제공된 경우(비전은 지원되지 않음).
        #   json.JSONDecodeError: 내부적으로 캡처됨; {"error": ..., "raw": ...} 형식으로 반환합니다.

        # 0. Rate limit 방지를 위한 호출 간격 조절
        now = time.monotonic()
        elapsed = now - self._last_call_time
        if elapsed < _MIN_CALL_INTERVAL:
            wait = _MIN_CALL_INTERVAL - elapsed
            logger.debug(f"Rate limit guard: waiting {wait:.1f}s before next LLM call")
            await asyncio.sleep(wait)

        # 1. 비전 호출 거부 — EXAONE은 이미지 입력을 지원하지 않음
        if image_url:
            raise ValueError(
                "Vision API is not supported by the current LLM model. "
                "Use OCR engine instead."
            )

        # 2. YAML 프롬프트 템플릿 로드
        guideline = await self.prompt_loader.load(prompt_file)

        # 파일이 dict가 아닌 일반 문자열로 로드되는 경우 처리
        if isinstance(guideline, str):
            if prompt_file.endswith(".yaml"):
                import yaml
                guideline_dict = yaml.safe_load(guideline)
                template = guideline_dict.get('template', '')
                max_tokens = guideline_dict.get('max_tokens')
            else:
                template = guideline
                max_tokens = None
        else:
            template = guideline.get('template', '')
            max_tokens = guideline.get('max_tokens')

        # 3. 템플릿 변수 대체 (안전한 포맷팅) 및 후행 공백/마킹문자열의 개행 제거
        # 핵심 버그 이유: Output:\\n 과 같이 개행으로 끝날경우 EXAONE이 무한 생성(Timeout)에 빠짐.
        user_content = template.format(**variables).strip()

        # 4. 메시지 리스트 생성 (채팅 포맷 준수)
        # 중요: 단일 system 메시지만 전송할 경우, Chat 모델들이 지침을 이어나가려 시도하며 
        # 공백(Space)이나 줄바꿈을 무한 생성하는 환각(Token Runaway)에 빠질 수 있습니다.
        # 따라서 본문을 User 메시지로 명확히 전달합니다.
        messages = [
            {
                "role": "system", 
                "content": "당신은 AI 어시스턴트입니다. 주어진 지침과 예시를 철저히 따르고, 부가 설명 없이 오직 결과물만 정확히 출력하십시오."
            },
            {
                "role": "user", 
                "content": user_content
            }
        ]

        # 5. API 호출 kwargs 구성
        kwargs = {
            "model": settings.LLM_MODEL_NAME,
            "messages": messages,
            "temperature": 0.1,  # 일관되고 구조화된 출력을 위해 낮은 temperature 설정
        }

        # 6. LLM 엔드포인트 호출 (Timeout 방지를 위해 stream=True 강제 사용)
        kwargs["stream"] = True

        # K-EXAONE 리즈닝 모델의 thinking 과정 비활성화 → 응답 속도 개선
        kwargs["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": False},
            "parse_reasoning": True,
        }

        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}
            
        full_content = ""
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                async for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    # reasoning_content (사고 과정)은 무시하고 실제 응답인 content만 수집
                    if delta.content is not None:
                        full_content += delta.content
                self._last_call_time = time.monotonic()
                break  # 성공 시 재시도 루프 탈출
            except RateLimitError as e:
                if attempt < _MAX_RETRIES - 1:
                    backoff = _BASE_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{_MAX_RETRIES}). "
                        f"Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)
                    full_content = ""  # 이전 부분 응답 초기화
                else:
                    logger.error(f"Rate limit exceeded after {_MAX_RETRIES} retries.")
                    raise

        if not full_content:
            if response_format == "json_object":
                return {"error": "Empty response", "raw": ""}
            return ""

        # 7. 파싱된 JSON 또는 일반 텍스트 반환
        if response_format == "json_object":
            try:
                return json.loads(full_content)
            except json.JSONDecodeError:
                return {"error": "Invalid JSON", "raw": full_content}

        return full_content.strip()


# 싱글톤 인스턴스 — 한 번 생성되어 애플리케이션 수명 주기 동안 재사용됨
_llm_handler_instance = None


def get_llm_handler() -> LLMHandler:
    # 설명: 애플리케이션 전체에 걸쳐 사용되는 싱글톤 LLMHandler 인스턴스를 반환합니다.
    # 작동 방식: 첫 호출 시 지연 초기화(Lazy instantiation)로 LLMHandler를 생성하고
    #            모듈 레벨 변수에 캐시합니다. 이후 호출은 캐시된 인스턴스를 반환하여
    #            클라이언트 초기화 반복을 방지합니다.
    # 반환값: 싱글톤 LLMHandler 인스턴스
    global _llm_handler_instance
    if _llm_handler_instance is None:
        _llm_handler_instance = LLMHandler()
    return _llm_handler_instance
