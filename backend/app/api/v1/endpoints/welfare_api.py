from fastapi import APIRouter, HTTPException
from app.schemas.summary import SummaryRequest, SummaryResponse
from app.logic.orchestrator import WelfareOrchestrator

router = APIRouter()

# 오케스트레이터 인스턴스 생성 (비즈니스 로직 관리)
orchestrator = WelfareOrchestrator()

@router.post("/process", response_model=SummaryResponse)
async def process_welfare_guide(request: SummaryRequest):
    """
    복지 정보 처리 엔드포인트
    - 요약 → 정제 → 검증 파이프라인 실행
    """
    try:
        # 오케스트레이터를 통해 전체 파이프라인 실행
        result = await orchestrator.process(request.content)
        
        return SummaryResponse(
            summary=result,
            status="success"
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"프롬프트 파일을 찾을 수 없습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"처리 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/summarize", response_model=SummaryResponse)
async def summarize_only(request: SummaryRequest):
    """요약만 수행"""
    try:
        result = await orchestrator.summarize(request.content)
        return SummaryResponse(summary=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refine", response_model=SummaryResponse)
async def refine_only(request: SummaryRequest):
    """정제만 수행"""
    try:
        result = await orchestrator.refine(request.content)
        return SummaryResponse(summary=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate", response_model=SummaryResponse)
async def validate_only(request: SummaryRequest):
    """검증만 수행"""
    try:
        result = await orchestrator.validate(request.content, request.content)  # ✅ 2개 인자
        return SummaryResponse(summary=result, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))