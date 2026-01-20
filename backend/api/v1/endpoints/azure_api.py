from fastapi import APIRouter, HTTPException
from backend.schemas.summary import SummaryRequest, SummaryResponse
from backend.services.azure_client import AzureOpenAIClient # 로직 임포트

router = APIRouter()
client = AzureOpenAIClient() # 클라이언트 인스턴스 생성

@router.post("/process", response_model=SummaryResponse)
async def process_azure_task(request: SummaryRequest):
    try:
        # KAN-12에서 구현한 비동기 비즈니스 로직 호출
        summary_result = await client.get_summary(request.content)
        return {"summary": summary_result, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))