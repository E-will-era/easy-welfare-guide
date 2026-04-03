import json
import uuid
import time
from typing import Dict, AsyncGenerator
from app.agents.llm_handler import get_llm_handler
from app.rag.engine import rag_engine
from app.ocr.engine import get_ocr_engine
from app.core.logger import logger
from app.core.config import settings


class WelfareOrchestrator:
    """
    설명: 전체 복지 문서 분석 파이프라인의 오케스트레이션을 담당하며 단계별 진행상황을
        SSE(Server-Sent Events) 형태로 클라이언트에 스트리밍합니다.

    작동 방식: OCR, 문서 분류, RAG 검색, 외부 MCP 검색, 대형언어모델(LLM)에 의한 요약본
        생성, 검증 단계들을 비동기 생성기 형태로 모두 연결합니다. 이후 퍼블릭(Public)
        메소드는 FastAPI StreamingResponse 응답에 알맞게 소비할 수 있도록 
        각 단계에서 생산된 정보들을 SSE 형태의 문자열로 전송해줍니다.
    """

    def __init__(self):
        """
        설명: 파이프라인 구성에 요구되는 하위 컴포넌트들로 WelfareOrchestrator를 초기화합니다.

        작동 방식: LLM 핸들러, RAG 엔진, OCR 엔진, 외부 MCP 검색 클라이언트들을 
            모두 싱글톤 형태로 불러오기 때문에 프로세스가 생겨날 때 
            가장 부하가 큰 작업(모델 호출 및 커넥션 풀 초기 등)이 오직 1회만 일어나도록 되어있습니다.
        
        반환값: 없음

        예외: 싱글톤 팩토리 호출 시에 나타나는 에러들(ImportError, RuntimeError 등)은 
            호출부(caller) 모델로 전파될 수 있습니다.
        """
        self.llm_handler = get_llm_handler()
        self.rag = rag_engine
        self.ocr_engine = get_ocr_engine()

    async def stream_welfare_flow(self, file_contents: bytes) -> AsyncGenerator[str, None]:
        """
        설명: 전체 복지 문서 분석 파이프라인을 실행하며 분석 완료 현황과 
            결과 데이터들을 SSE 형태로 스트리밍하여 반환합니다.

        작동 방식:
            Step 1  - OCR: 업로드된 이미지에서 OCREngine 모듈을 거쳐 텍스트를 파싱하여 추출.
            Step 2  - Classification: 추출된 내용이 복지 문서와 연관되어있는지 확인.
            Step 3  - RAG search: 문서 안에서 질의를 위한 키워드를 선별하고 지정된 
                      데이터소스 저장소로부터 맥락(context) 정보 수집.
            Step 3.5 - MCP external search: 공공 데이터 포탈 (복지로 등)의 라이브 정보를 추가
                      보충자료로 호출 사용 (정상 호출되지 않아도 넘어감).
            Step 4  - Admin summary: RAG 및 문서 자료들 토대로 복잡한 행정 전문 지식이 
                      정리된 원문 요약 리포트(Summary)를 구성.
            Step 5  - Plain language refiner: 원문 요약 내용을 13세 이하 어린이도 
                      쉽게 내용을 파악가능한 쉬운 평문으로 다시 가공 구성.
            Step 6  - Validation: 원본 결과치 내의 데이터와 대조해 평문 내에서의 
                      할루시네이션(환각) 거짓 유무 검토 평가.
            Step 7  - Completion: 전체 정리 리포트를 클라이언트에게 최후 반환하며 세션
                      ID 값을 기록해 하위 과정에서도 연속성있게 추적.

        반환값: SSE-formatted된 형식 문자열을 뱉어내는 비동기(AsyncGenerator) 생성기.
        예외: 파이프라인 내부에서의 모든 런타임 오류는 즉시 포착되어 별도의 에러스트림 
            처리가되어 SSE-Error 이벤트 객체로 호출자에게 예외 반환. (전파되지 않음)
        """
        task_id = uuid.uuid4().hex
        total_start_time = time.perf_counter()

        try:
            # [Step 1] Image -> Text (OCR)
            step_start = time.perf_counter()

            ocr_result = await self.ocr_engine.extract_text(file_contents)
            extracted_text = ocr_result['text']

            logger.info(f"[Phase 1] OCR: {time.perf_counter() - step_start:.2f}s")

            if not extracted_text:
                yield self._error_event("Text extraction failed")
                return

            # OCR 이후 공통 파이프라인 실행
            async for event in self._run_analysis_pipeline(extracted_text, task_id, total_start_time):
                yield event

        except Exception as e:
            logger.error(f"Streaming Error: {str(e)}")
            yield self._error_event(f"Server error: {str(e)}")

    async def stream_text_flow(self, text: str) -> AsyncGenerator[str, None]:
        """
        설명: 사용자가 직접 입력한 텍스트를 분석하는 파이프라인입니다.
            OCR 단계를 건너뛰고 분류부터 시작합니다.
        """
        task_id = uuid.uuid4().hex
        total_start_time = time.perf_counter()

        try:
            if not text or not text.strip():
                yield self._error_event("텍스트가 비어있습니다.")
                return

            async for event in self._run_analysis_pipeline(text.strip(), task_id, total_start_time):
                yield event

        except Exception as e:
            logger.error(f"Text Streaming Error: {str(e)}")
            yield self._error_event(f"Server error: {str(e)}")

    async def _run_analysis_pipeline(self, extracted_text: str, task_id: str, total_start_time: float) -> AsyncGenerator[str, None]:
        """
        설명: 분류 → RAG → 요약 → 검증까지의 공통 분석 파이프라인입니다.
        """
        # [Step 2] Relevance classification
        step_start = time.perf_counter()
        is_welfare_str = await self.llm_handler.run_prompt_template(
            prompt_file="classifier.yaml",
            variables={"input": extracted_text[:1000]}
        )

        if "true" not in is_welfare_str.lower():
            yield self._error_event("The document does not appear to be welfare-related.")
            return

        logger.info(f"[Phase 2] Classify: {time.perf_counter() - step_start:.2f}s")
        yield self._progress_event("relevance")

        # [Step 3] RAG retrieval and query generation
        step_start = time.perf_counter()

        search_query = await self.llm_handler.run_prompt_template(
            prompt_file="query_gen.yaml",
            variables={"input": extracted_text[:1000]}
        )
        logger.info(f"[Phase 3a] Query Gen: {time.perf_counter() - step_start:.2f}s | query='{search_query[:100]}'")

        rag_start = time.perf_counter()
        rag_results = await self.rag.search(search_query, top_k=3)
        context_text = "\n".join([f"- {doc['content']}" for doc in rag_results])

        logger.info(f"[Phase 3b] RAG Search: {time.perf_counter() - rag_start:.2f}s ({len(rag_results)} docs)")
        logger.info(f"[Phase 3] Total: {time.perf_counter() - step_start:.2f}s")
        yield self._progress_event("search")

        # [Step 4] Admin Summary
        step_start = time.perf_counter()

        admin_summary = await self.llm_handler.run_prompt_template(
            prompt_file="admin_summary.yaml",
            variables={
                "context": context_text,
                "input": extracted_text
            }
        )

        logger.info(f"[Phase 4] Admin Summary: {time.perf_counter() - step_start:.2f}s")
        yield self._progress_event("summarize")

        # [Step 5] Plain language refiner
        step_start = time.perf_counter()

        plain_summary = await self.llm_handler.run_prompt_template(
            prompt_file="easy_refiner.yaml",
            variables={"input": admin_summary}
        )

        logger.info(f"[Phase 5] Refine: {time.perf_counter() - step_start:.2f}s")
        yield self._progress_event("translate")

        # [Step 6] Validation
        step_start = time.perf_counter()

        validation_result = await self.llm_handler.run_prompt_template(
            prompt_file="verification.yaml",
            variables={
                "original": admin_summary,
                "target": plain_summary
            },
            response_format="json_object"
        )

        logger.info(f"[Phase 6] Validate: {time.perf_counter() - step_start:.2f}s - {validation_result.get('passed')}")
        yield self._progress_event("validate")

        # [Step 7] Completion — create session for downstream eligibility checks
        from app.core.session_manager import get_session_manager
        session_id = get_session_manager().create_session()
        get_session_manager().store_analysis_context(session_id, {
            "admin_summary": admin_summary,
            "plain_summary": plain_summary,
            "extracted_text": extracted_text
        })

        final_data = {
            "task_id": task_id,
            "admin_summary": admin_summary,
            "plain_summary": plain_summary,
            "references": [{"title": r['metadata'].get('title'), "resource": r['metadata'].get('url')} for r in rag_results],
            "validation": validation_result,
            "session_id": session_id
        }

        logger.info(f"Process Complete: {time.perf_counter() - total_start_time:.2f}s")
        yield self._format_sse("completed", final_data)

    async def stream_retry_flow(self, admin_summary: str) -> AsyncGenerator[str, None]:
        """
        설명: 더 심플하고 낮은 읽기 레벨을 대상으로 하는 평문 번역(plain language 
            refinement) 과정을 수행하고 그 결과를 SSE 이벤트화 하여 제공합니다.

        작동 방식:
            Step 1 - Retry refiner: 기본의 admin_summary 원본에 대해 더 쉬운 수준을 의도한 
                     retry_refiner 템플릿을 통해 평문을 다시 생성 및 가공.
            Step 2 - Validation: 새로 도출해낸 plain summary 본문 문장이 원본의 데이터를 
                     제대로 참조하고있는지 (환각) 재검증 절차.
            Step 3 - Completion: 최종으로 산출된 모든 변형 본문 이벤트 결과를 방출.

        반환값: SSE-formatted된 형식 문자열을 뱉어내는 비동기(AsyncGenerator) 생성기.
        예외: 모든 에러는 내부 에러 핸들러 단에서 감지되고 런타임 외부 호출자(caller) 
            에게는 에러 텍스트가 SSE 에러 스트림을 통해 통보됩니다.
        """
        try:
            # [Step 1] Re-refine to simpler plain language (Retry Refiner)
            step_start = time.perf_counter()
            yield self._progress_event("re_translate")

            retry_plain_summary = await self.llm_handler.run_prompt_template(
                prompt_file="retry_refiner.yaml",
                variables={"input": admin_summary}
            )

            logger.info(f"[Retry Phase 1] Refine: {time.perf_counter() - step_start:.2f}s")

            # [Step 2] Hallucination validation (Validator)
            step_start = time.perf_counter()
            yield self._progress_event("validate")

            validation_result = await self.llm_handler.run_prompt_template(
                prompt_file="verification.yaml",
                variables={
                    "original": admin_summary,
                    "target": retry_plain_summary
                },
                response_format="json_object"
            )

            logger.info(f"[Retry Phase 2] Validate: {time.perf_counter() - step_start:.2f}s")

            # [Step 3] Send completion event
            final_data = {
                "admin_summary": admin_summary,
                "retry_plain_summary": retry_plain_summary,
                "validation": validation_result
            }

            logger.info("Retry Process Complete")
            yield self._format_sse("completed", final_data)

        except Exception as e:
            logger.error(f"Retry Streaming Error: {str(e)}")
            yield self._error_event(f"Server error: {str(e)}")

    def _format_sse(self, event_type: str, data: Dict) -> str:
        """
        설명: 데이터 딕셔너리를 표준 SSE 이벤트 형식 포맷의 문자열로 가공합니다.

        작동 방식: 직렬화된 dict JSON 자료 구조에 대해 한국어 텍스트 문자가 깨지지 
            않게 ensure_ascii=False 변환기를 사용하여 변환하며 SSE 포맷 표준 양식인
            'event: <type>\\ndata: <json>\\n\\n' 포맷안으로 끼워 맞춥니다.

        반환값: 파싱 완료된 즉시 스트리밍 반응 응답(SSE-formatted) 문자열.
        예외: 없음 — 인자로 주어진 값들이 json.dumps 가능한 구조만 의존.
        """
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _progress_event(self, phase: str) -> str:
        """
        설명: 현재 파이프라인의 진행 상태를 나타내는 진행 안내 이벤트를 파싱해냅니다.

        작동 방식: _format_sse 내부 메소드로 상태명을 'progress'라는 형태로 지정하여
            백엔드와 프론트엔드가 서로 동의한 형태 { status, data: { phase } }의 양식
            대로 보내주는 책임을 갖습니다.

        반환값: SSE-formatted된 형식 진행 메시지 (progress event string).
        예외: 없음.
        """
        return self._format_sse("progress", {"status": "processing", "data": {"phase": phase}})

    def _error_event(self, message: str) -> str:
        """
        설명: 사람이 식별할 수 있는 문장 구문으로 파이프라인 내부 에러를 알리는 SSE 생성기.

        작동 방식: 내부의 _format_sse 유틸 모듈을 통해 프론트엔드가 약속 및 동의해놓은
            에러 페이로드 규격 { status, data: { message } } 을 따라 호출자 쪽으로
            오류 원인을 나타냅니다.
            
        반환값: SSE-formatted 에러 이벤트 포맷팅 문자열.
        예외: 없음.
        """
        return self._format_sse("error", {"status": "failed", "data": {"message": message}})
