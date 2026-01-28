"""
복지 이미지 처리 API (간소화 버전)
이미지 업로드 → LLM OCR → 복지 관련성 판단 + 키워드 추출 → 결과 반환
"""
import json
import base64
from typing import Dict, List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.agents.llm_handler import get_llm_handler

router = APIRouter()


# ============= Response Models =============

class ImageProcessResult(BaseModel):
    """이미지 처리 최종 결과"""
    success: bool
    
    # OCR 결과
    extracted_text: str
    
    # 키워드 추출
    keywords: List[str]
    is_welfare_related: bool  # 복지 관련 문서인가?
    confidence: float  # 복지 관련 신뢰도 (0.0-1.0)
    
    # 카테고리 힌트
    category_hints: Optional[List[str]] = None  # 청년, 주거, 교육 등
    
    # 추가 정보
    message: Optional[str] = None
    suggestions: Optional[List[str]] = None  # 사용자 가이드


# ============= Main Endpoint =============

@router.post("/process-welfare-image", response_model=ImageProcessResult)
async def process_welfare_image(file: UploadFile = File(...)):
    """
    복지 이미지 처리
    
    Flow:
    1. 이미지 업로드
    2. LLM으로 OCR 텍스트 추출
    3. 복지 관련성 판단 + 키워드 추출
    4. 결과 반환
    """
    try:
        # Step 1: 이미지 읽기
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        # Step 2: LLM OCR + 키워드 추출
        handler = get_llm_handler()
        ocr_result = await extract_welfare_keywords(handler, base64_image)
        
        # 복지 관련 문서가 아니면 조기 종료
        if not ocr_result["is_welfare_related"]:
            return ImageProcessResult(
                success=False,
                extracted_text=ocr_result["text"],
                keywords=[],
                is_welfare_related=False,
                confidence=ocr_result["confidence"],
                category_hints=[],
                message="복지 관련 문서가 아닙니다.",
                suggestions=[
                    "복지 공고문, 신청서, 안내문을 업로드해주세요.",
                    "텍스트가 명확하게 보이는 이미지를 사용해주세요."
                ]
            )
        
        # Step 3: 성공 결과 반환
        return ImageProcessResult(
            success=True,
            extracted_text=ocr_result["text"],
            keywords=ocr_result["keywords"],
            is_welfare_related=True,
            confidence=ocr_result["confidence"],
            category_hints=ocr_result.get("category_hints", []),
            message="복지 관련 문서로 판단되었습니다.",
            suggestions=[
                "추출된 키워드로 복지 프로그램을 검색할 수 있습니다.",
                "텍스트 내용을 확인하여 신청 조건을 파악하세요."
            ]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"이미지 처리 실패: {str(e)}"
        )


# ============= Helper Functions =============

async def extract_welfare_keywords(handler, base64_image: str) -> Dict:
    """
    LLM으로 OCR + 복지 키워드 추출
    """
    response = await handler.client.chat.completions.create(
        model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """이 이미지를 분석하여 다음을 수행하세요:

1. 모든 텍스트를 추출하세요 (OCR)
2. 복지 관련 문서인지 판단하세요
3. 핵심 키워드를 추출하세요 (대상, 지원내용, 조건 등)

JSON 형식으로 응답:
{
    "text": "추출된 전체 텍스트",
    "is_welfare_related": true/false,
    "confidence": 0.0-1.0,
    "keywords": ["키워드1", "키워드2", ...],
    "category_hints": ["청년", "주거", "교육" 등 카테고리 힌트]
}

복지 관련 단어 예시: 지원, 혜택, 신청, 대상, 자격, 조건, 보조금, 수당, 복지"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        max_tokens=2000,
        temperature=0.1
    )
    
    # JSON 파싱
    content = response.choices[0].message.content
    if content.startswith("```json"):
        content = content.split("```json")[1].split("```")[0].strip()
    elif content.startswith("```"):
        content = content.split("```")[1].split("```")[0].strip()
    
    return json.loads(content)


# ============= Optional: 텍스트 전용 키워드 추출 =============

@router.post("/extract-keywords-from-text")
async def extract_keywords_from_text(text: str):
    """
    이미지 없이 텍스트로만 키워드 추출
    (OCR 결과를 직접 붙여넣는 경우)
    """
    try:
        handler = get_llm_handler()
        
        # 텍스트에서 키워드 추출
        keywords_result = await handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "복지 관련 핵심 키워드를 추출하세요."
                },
                {
                    "role": "user",
                    "content": f"""다음 텍스트에서 복지 검색용 키워드를 추출하세요:

{text}

JSON 형식:
{{
    "keywords": ["키워드1", "키워드2", ...],
    "is_welfare_related": true/false,
    "confidence": 0.0-1.0,
    "category_hints": ["카테고리1", "카테고리2", ...]
}}"""
                }
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        content = keywords_result.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        
        if not result["is_welfare_related"]:
            return {
                "success": False, 
                "message": "복지 관련 내용이 아닙니다.",
                "keywords": [],
                "confidence": result.get("confidence", 0.0)
            }
        
        return {
            "success": True,
            "keywords": result["keywords"],
            "is_welfare_related": True,
            "confidence": result.get("confidence", 0.0),
            "category_hints": result.get("category_hints", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))