from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from fastapi.responses import StreamingResponse

from app.logic.orchestrator import WelfareOrchestrator

router = APIRouter()
orchestrator = WelfareOrchestrator()

# --- [Endpoints] ---

@router.post("/analyze")
async def analyze_welfare_document(file: UploadFile = File(...)):
    """
    설명: 업로드된 복지 문서 이미지를 입력받아 전체 분석 파이프라인의 결과를
        Server-Sent Events(SSE)로 스트리밍합니다.

    작동 방식: 업로드된 파일 바이트를 읽어 WelfareOrchestrator.stream_welfare_flow에
        전달합니다. 해당 파이프라인은 OCR, 문서 분류, RAG + MCP 검색, 요약, 검증을
        수행합니다. 각 파이프라인 단계는 진행 상황을 알리는 SSE 이벤트를 방출하며,
        최종 단계에서는 admin_summary, plain_summary, references, validation,
        session_id가 포함된 완료 이벤트를 반환합니다.

    반환값: orchestrator 생성기에서 생성된 SSE 이벤트를 포함하는 text/event-stream
        형태의 StreamingResponse.

    예외: 여기서 발생하는 HTTP 예외는 없으며 스트리밍 도중 발생한 파이프라인 오류는
        'failed' 상태를 가진 SSE 이벤트 형태(error event)로 전달됩니다.
    """
    contents = await file.read()
    return StreamingResponse(
        orchestrator.stream_welfare_flow(contents),
        media_type="text/event-stream"
    )


@router.post("/retry")
async def retry_welfare_summary(
    admin_summary: str = Body(..., embed=True, description="Admin summary text received from a previous /analyze response")
):
    """
    설명: 기존의 행정 요약본(admin_summary)을 기반으로 더 쉬운 읽기 수준을 
        대상으로 하는 평문 요약(plain language summary)을 재요청하며,
        도출된 결과를 Server-Sent Events(SSE)로 스트리밍합니다.

    작동 방식: 입력받은 admin_summary가 비어있지 않은지 검증한 후,
        WelfareOrchestrator.stream_retry_flow로 전달합니다. Orchestrator는
        retry_refiner 프롬프트를 실행하고 출력물을 다시 검증한 뒤 
        완료된 SSE 이벤트(retry_plain_summary 및 validation 포함)를 반환합니다.

    반환값: orchestrator의 재요청(retry) 생성기에서 생성된 SSE 이벤트를 
        포함하는 text/event-stream 형태의 StreamingResponse.

    예외: admin_summary가 비어 있거나 공백문자만 있는 경우 HTTPException(400) 발생.
        파이프라인 스트리밍 중 나타난 에러는 SSE 에러 이벤트로 전달됩니다.
    """
    if not admin_summary.strip():
        raise HTTPException(status_code=400, detail="admin_summary must not be empty.")

    return StreamingResponse(
        orchestrator.stream_retry_flow(admin_summary),
        media_type="text/event-stream"
    )

@router.post("/analyze-text")
async def analyze_welfare_text(text: str = Body(..., embed=True, description="Text to be analyzed")):
    """
    설명: 사용자가 직접 입력한 복지 관련 텍스트를 분석합니다.
        OCR 단계를 건너뛰고 분류부터 시작하는 파이프라인입니다.
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty.")

    return StreamingResponse(
        orchestrator.stream_text_flow(text),
        media_type="text/event-stream"
    )
