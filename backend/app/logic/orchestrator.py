import base64
import json
import uuid
import time  # [추가] 시간 측정을 위한 모듈
from typing import Dict, List, Optional, AsyncGenerator
from fastapi import HTTPException

from app.agents.llm_handler import get_llm_handler
from app.rag.engine import rag_engine
from app.core.config import settings
from app.core.logger import logger

class WelfareOrchestrator:
    def __init__(self):
        self.llm_handler = get_llm_handler()
        self.rag = rag_engine

    async def stream_welfare_flow(self, file_contents: bytes) -> AsyncGenerator[str, None]:
        """
        [SSE 지원] 8단계 흐름을 실시간 이벤트 스트림으로 전송
        Yields:
            "event: <type>\ndata: <json>\n\n" 형태의 SSE 문자열
        """
        # 전체 프로세스 시작 시간
        task_id = uuid.uuid4().hex
        total_start_time = time.perf_counter()

        try:
            # 1. 이미지 처리 후 텍스트 추출 과정
            step_start = time.perf_counter()

            base64_image = base64.b64encode(file_contents).decode('utf-8')
            extracted_text = await self._extract_text_from_image(base64_image)
            
            logger.info(f"[Phase 1] image2text: {time.perf_counter() - step_start:.2f}s")
            
            if not extracted_text:
                yield self._format_sse("error", {
                    "status": "failed",
                    "data": {
                        "phase": "close",
                        "message": "이미지에서 텍스트를 추출하지 못했습니다."
                    }
                })
                return

            # 2. 서비스 관련 내용인지 검증
            step_start = time.perf_counter()
            is_welfare = await self._check_welfare_relevance(extracted_text)

            if not is_welfare:
                yield self._format_sse("error", {
                    "status": "failed",
                    "data": {
                        "phase": "close",
                        "message": "복지 관련 이미지가 아닙니다."
                    }
                })
                return

            logger.info(f"[Phase 2] validate: {time.perf_counter() - step_start:.2f}s")
            
            yield self._format_sse("progress", {
                "status": "pending", 
                "data": {
                    "phase": "relevance"
                }
            })

            # 3. RAG 검색
            step_start = time.perf_counter()

            search_query = await self._generate_search_query(extracted_text)
            rag_results = await self.rag.search(search_query, top_k=3)
            
            # [🔍 디버깅용 로그 추가]
            logger.info(f"🧐 생성된 검색 쿼리: [{search_query}]")
            logger.info(f"🔍 검색된 문서 개수: {len(rag_results)}개") # <--- 이 로그 확인 필요
            logger.info(f"🔍 검색 결과 상세: {json.dumps(rag_results, ensure_ascii=False, default=str)}")

            context_text = "\n".join([f"- {doc['content']}" for doc in rag_results])

            logger.info(f"[Step 3] RAG를 검색합니다: {time.perf_counter() - step_start:.2f}s")
            
            yield self._format_sse("progress", {
                "status": "processing", 
                "data": {
                    "phase": "search"
                }
            })

            # 3. 추출된 텍스트와 RAG 문서로 내용 요약
            step_start = time.perf_counter()
            admin_summary = await self._create_admin_summary(extracted_text, context_text)

            logger.info(f"[Step 4] 이미지에서 추출한 텍스트와 RAG에서 검색된 문서를 요약합니다: {time.perf_counter() - step_start:.2f}s")
            
            yield self._format_sse("progress", {
                "status": "processing", 
                "data": {
                    "phase": "summarize"
                }
            })

            # 4. 요악된 용어를 순화어로 제공
            step_start = time.perf_counter()
            plain_summary = await self._create_plain_summary(admin_summary)

            logger.info(f"[Step 5] 요악된 내용에서 행정 용어를 순화어로 변환합닌다: {time.perf_counter() - step_start:.2f}s")
            
            yield self._format_sse("progress", {
                "status": "processing", 
                "data": {
                    "phase": "translate"
                }
            })

            # --- [Step 7] 검증 ---
            step_start = time.perf_counter()
            validation_result = await self._validate_summaries(admin_summary, plain_summary)

            logger.info(f"[Step 6] 행정 용어와 순화어로 변환된 요약 내용이 일치하는지 검증합니다: {time.perf_counter() - step_start:.2f}s")
            
            if not validation_result['passed']:
                logger.warning(f"검증 경고: {validation_result.get('reason')}")
            
            yield self._format_sse("progress", {
                "status": "processing", 
                "data": {
                    "phase": "validate"
                }
            })

            # --- [Step 8] 최종 결과 전송 ---
            references = []

            for res in rag_results:
                meta = res.get("metadata", {})
                references.append({
                    "title": meta.get("title"),
                    "resource": meta.get("url")
                })

            final_data = {
                "task_id": task_id,
                "admin_summary": admin_summary,
                "plain_summary": plain_summary,
                "references": references,
            }
            
            logger.info(f"✅ Total Process Time: {time.perf_counter() - total_start_time:.2f}s")

            # 최종 데이터는 'completed' 이벤트로 전송
            yield self._format_sse("completed", final_data)

        except Exception as e:
            logger.error(f"Streaming Error: {str(e)}")

            yield self._format_sse("error", {
                "status": "failed", 
                "data": {
                    "phase": "error",
                    "message": f"서버 오류: {str(e)}"
                }
            })

    def _format_sse(self, event_type: str, data: Dict) -> str:
        """데이터를 SSE 포맷 문자열로 변환"""
        # 한글 깨짐 방지를 위해 ensure_ascii=False 사용
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    # --- 내부 메서드 (Agents) ---
    # (아래 메서드들은 기존 코드와 동일하므로 생략하지 않고 그대로 유지합니다)

    async def _extract_text_from_image(self, base64_image: str) -> str:
        """OCR 에이전트"""
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이미지에 있는 모든 텍스트를 있는 그대로 추출해줘."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=1500
        )
        return response.choices[0].message.content.strip()

    async def _check_welfare_relevance(self, text: str) -> bool:
        """관련성 검증 에이전트"""
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "입력된 텍스트가 복지 공고문, 안내문, 신청서라면 'true', 아니면 'false'만 답하세요."},
                {"role": "user", "content": text[:1000]}
            ],
            temperature=0.0
        )
        return "true" in response.choices[0].message.content.lower()

    async def _generate_search_query(self, text: str) -> str:
        """검색 쿼리 생성 에이전트"""
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "텍스트에서 복지 정책 검색을 위한 핵심 키워드 추출하여 공백으로 구분해 주세요."},
                {"role": "user", "content": text[:1000]}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content.strip()

    async def _create_admin_summary(self, user_text: str, context: str) -> str:
        """Step 5: Admin Summary 생성 (행정용어, ### 강조)"""
        prompt = f"""
당신은 행정 문서 요약 전문가입니다.
사용자 입력(Input)과 RAG 검색 결과(Context)를 종합하여 요약하세요.

[필수 지침]
1. **행정 용어**를 그대로 사용하세요. (순화하지 마세요)
2. 핵심 키워드(대상, 금액, 기간, 조건) 앞에는 반드시 `###`을 붙여서 강조하세요.
   (예: ###중위소득 100% 이하, ###매월 25일 지급)
3. 전체 길이는 공백 포함 **200자 내외**로 작성하세요.
4. 문단은 명확하게 구성하세요.

[Context (RAG)]
{context}

[Input (OCR)]
{user_text}
"""
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    async def _create_plain_summary(self, admin_summary: str) -> str:
        """Step 6: Plain Summary 생성 (중/초등 수준 순화)"""
        prompt = f"""
당신은 초등학교 선생님입니다.
아래의 [행정 요약문]을 초등학생이나 중학생도 쉽게 이해할 수 있도록 바꿔주세요.

[지침]
1. `###` 기호는 모두 제거하세요.
2. 어려운 행정 용어는 쉬운 말로 풀어서 설명하세요.
3. 친절하고 부드러운 말투를 사용하세요.
4. 내용은 원본과 동일해야 합니다.

[행정 요약문]
{admin_summary}
"""
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()

    async def _validate_summaries(self, admin_sum: str, plain_sum: str) -> Dict:
        """Step 7: 환각 검증"""
        prompt = f"""
두 요약문을 비교하여 내용이 정확히 일치하는지 검증하세요.

[행정 요약(원본)]
{admin_sum}

[순화 요약(타겟)]
{plain_sum}

[검증 기준]
1. 순화 과정에서 금액, 날짜, 나이 등 핵심 숫자가 변경되지 않았는가?
2. 원본에 없는 혜택을 지어내지 않았는가? (환각 검사)

JSON 형식으로 응답하세요:
{{
    "passed": true/false,
    "reason": "실패 시 이유"
}}
"""
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "JSON 형식으로만 응답하세요."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        return json.loads(response.choices[0].message.content)

    async def stream_retry_flow(self, admin_summary: str) -> AsyncGenerator[str, None]:
        """
        [SSE] 재요청(Retry) 흐름: Admin Summary를 받아 더 쉬운 표현(Level 7)으로 변환
        """
        task_id = uuid.uuid4().hex
        start_time = time.perf_counter()

        try:
            # 1. 난이도 재조정 알림
            yield self._format_sse("progress", {
                "status": "pending",
                "data": {
                    "phase": "analyze_difficulty",
                    "message": "더 쉬운 표현(유치원/비유)으로 난이도를 조정합니다."
                }
            })
            
            # 2. Level 7(유치원) 수준으로 재순화 수행
            step_start = time.perf_counter()
            
            # llm_handler의 refine 메서드 호출 (level=7 적용)
            # refiner.yaml의 level_7 규칙("추상적인 개념을 '비유'로 치환")을 따름
            retry_plain_summary = await self.llm_handler.refine(admin_summary, level=7)
            
            logger.info(f"[Retry] Re-refining to Level 7: {time.perf_counter() - step_start:.2f}s")
            
            yield self._format_sse("progress", {
                "status": "processing",
                "data": {
                    "phase": "re_translate",
                    "message": "이해하기 쉽도록 비유를 사용하여 설명을 고치고 있습니다."
                }
            })

            # 3. 안전성 검증 (Original Admin Summary vs New Easy Summary)
            step_start = time.perf_counter()
            validation_result = await self._validate_summaries(admin_summary, retry_plain_summary)
            
            logger.info(f"[Retry] Validation: {time.perf_counter() - step_start:.2f}s")
            
            if not validation_result['passed']:
                logger.warning(f"[Retry] Validation Warning: {validation_result.get('reason')}")

            yield self._format_sse("progress", {
                "status": "processing",
                "data": {
                    "phase": "validate",
                    "message": "내용의 정확성을 검증하고 있습니다."
                }
            })

            # 4. 최종 결과 전송
            final_data = {
                "task_id": task_id,
                "admin_summary": admin_summary, # 비교를 위해 원본 포함
                "retry_plain_summary": retry_plain_summary,     # 프론트엔드 키 통일을 위해 plain_summary로 전달하거나 retry_plain_summary 구분 가능
                "validation": validation_result
            }
            
            logger.info(f"✅ Retry Process Completed: {time.perf_counter() - start_time:.2f}s")
            yield self._format_sse("completed", final_data)

        except Exception as e:
            logger.error(f"Retry Streaming Error: {str(e)}")
            yield self._format_sse("error", {
                "status": "failed",
                "data": {
                    "phase": "error",
                    "message": f"재요청 처리 중 오류가 발생했습니다: {str(e)}"
                }
            })