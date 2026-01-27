"""
복지 정보 처리 API
- 단일 엔드포인트: POST /api/v1/analyze
- 이미지 파일 또는 텍스트 입력 → 처리 → 결과 반환
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
import base64

from app.logic.orchestrator import WelfareOrchestrator

router = APIRouter()
orchestrator = WelfareOrchestrator()


# ============= Response Model =============

class Reference(BaseModel):
    """참고 문서"""
    title: str
    resource: str


class AnalyzeData(BaseModel):
    """분석 결과 데이터"""
    task_id: str
    admin_summary: str
    plain_summary: str
    references: list[Reference] = []


class AnalyzeResponse(BaseModel):
    """분석 응답 (API 명세서 준수)"""
    status: str  # "completed" or "failed"
    data: AnalyzeData


# ============= Main Endpoint =============

@router.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_welfare_document(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    """
    복지 문서 분석 API
    
    처리 흐름:
    1. 입력 → 텍스트 추출 (이미지면 OCR, 텍스트면 그대로)
    2. 복지 관련성 검증
    3. 요약
    4. 순화어 변환 (13세 수준)
    5. 검증 (원본-요약 일치 확인)
    6. 결과 반환
    
    Input:
        - file: 업로드할 이미지 파일 (PNG, JPG, PDF)
        - text: 직접 입력한 텍스트
        
        * file 또는 text 중 하나는 필수
    
    Output (API 명세서 준수):
        {
            "status": "completed",
            "data": {
                "task_id": string,
                "admin_summary": string,
                "plain_summary": string,
                "references": [
                    {
                        "title": string,
                        "resource": string
                    }
                ]
            }
        }
    """
    try:
        # Step 1: 입력 검증
        if not file and not text:
            raise HTTPException(
                status_code=400,
                detail="파일 또는 텍스트 중 하나는 반드시 제공되어야 합니다."
            )
        
        # Step 2: 텍스트 추출
        extracted_text = ""
        
        if file:
            # 이미지 파일 → OCR
            contents = await file.read()
            base64_image = base64.b64encode(contents).decode('utf-8')
            extracted_text = await orchestrator.extract_text_from_image(base64_image)
        else:
            # 텍스트 직접 입력
            extracted_text = text
        
        if not extracted_text or len(extracted_text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="텍스트 추출에 실패했습니다. 이미지가 명확한지 확인해주세요."
            )
        
        # Step 3: 복지 관련성 검증
        is_welfare = await orchestrator.check_welfare_relevance(extracted_text)
        
        if not is_welfare:
            # 복지 관련 아닌 경우 400 에러 반환
            raise HTTPException(
                status_code=400,
                detail="복지 관련 문서가 아닙니다. 복지 공고문, 신청서, 안내문을 업로드해주세요."
            )
        
        # Step 4: 요약
        admin_summary = await orchestrator.summarize(extracted_text)
        
        # Step 5: 순화어 변환 (13세 수준)
        plain_summary = await orchestrator.refine(admin_summary)
        
        # Step 6: 검증 (원본-요약 일치 확인)
        validation_result = await orchestrator.validate(extracted_text, plain_summary)
        
        if not validation_result["passed"]:
            raise HTTPException(
                status_code=500,
                detail="검증 실패: 요약 내용이 원본과 일치하지 않습니다."
            )
        
        # Step 7: 결과 반환 (API 명세서 형식)
        import hashlib
        task_id = hashlib.md5(extracted_text.encode()).hexdigest()[:16]
        
        return AnalyzeResponse(
            status="completed",
            data=AnalyzeData(
                task_id=task_id,
                admin_summary=admin_summary,
                plain_summary=plain_summary,
                references=[]  # 현재는 빈 배열, 향후 RAG 구현 시 추가
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"처리 중 오류가 발생했습니다: {str(e)}"
        )