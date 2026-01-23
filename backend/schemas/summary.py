from pydantic import BaseModel, Field
from typing import Optional

class SummaryRequest(BaseModel):
    """복지 정보 처리 요청"""
    content: str = Field(
        ...,
        min_length=1,
        description="처리할 복지 정보 원문",
        example="이 사업은 중위소득 150% 이하 가구를 대상으로 월 30만원의 바우처를 제공합니다."
    )

class SummaryResponse(BaseModel):
    """복지 정보 처리 응답"""
    summary: str = Field(
        ...,
        description="처리된 결과 (요약/정제/검증)",
        example="중위소득 150% 이하 가구에 월 30만원 바우처 지급"
    )
    status: str = Field(
        default="success",
        description="처리 상태",
        example="success"
    )

class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str = Field(
        ...,
        description="에러 상세 메시지",
        example="프롬프트 파일을 찾을 수 없습니다"
    )
    status: str = Field(
        default="error",
        description="에러 상태",
        example="error"
    )