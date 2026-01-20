from pydantic import BaseModel

class SummaryRequest(BaseModel):
    content: str  # 요약할 원문

class SummaryResponse(BaseModel):
    summary: str  # 요약된 결과
    status: str = "success"