from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from fastapi.responses import StreamingResponse  # [필수] 추가
from app.logic.orchestrator import WelfareOrchestrator

router = APIRouter()
orchestrator = WelfareOrchestrator()

@router.post("/analyze")
async def analyze_welfare_document(file: UploadFile = File(...)):
    """
    [SSE] 복지 문서 분석 실시간 스트리밍 API
    """
    try:
        contents = await file.read()
        
        # [수정됨] await orchestrator.process_welfare_flow(...) 라고 쓰면 에러가 납니다!
        # 대신 StreamingResponse에 제너레이터 함수 자체를 넘겨줘야 합니다.
        return StreamingResponse(
            orchestrator.stream_welfare_flow(contents), # 함수 호출 결과를 바로 전달 (await 없음)
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")

# Retry 엔드포인트 구현
@router.post("/retry")
async def retry_welfare_summary(
    admin_summary: str = Body(..., embed=True, description="이전 분석 결과로 받은 행정 요약문")
):
    """
    [SSE] 요약 재요청 API (Level 7 난이도 하향 조정)
    
    Args:
        admin_summary (str): JSON Body {"admin_summary": "내용..."} 형태로 전달
    
    Returns:
        StreamingResponse: SSE 이벤트 스트림
    """
    try:
        # orchestrator의 stream_retry_flow 호출
        return StreamingResponse(
            orchestrator.stream_retry_flow(admin_summary),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"재요청 처리 오류: {str(e)}")