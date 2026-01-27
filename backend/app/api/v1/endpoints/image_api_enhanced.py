import json
import base64
from typing import Dict, List, Optional
from openai import AsyncAzureOpenAI
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

# 누락된 import 추가
from app.core.config import settings
from app.agents.llm_handler import get_llm_handler

# ============= 새로운 API 엔드포인트 =============

router = APIRouter()

class ImageQualityResponse(BaseModel):
    is_acceptable: bool
    quality_score: int
    resolution: str
    issues: List[str]
    recommendations: List[str]

class KeyInformationResponse(BaseModel):
    # Optional로 변경하여 None 값 허용
    document_type: Optional[str] = "알 수 없음"
    target_audience: Optional[str] = "정보 없음"
    benefits: Optional[List[str]] = []
    eligibility: Optional[Dict] = {}
    application_method: Optional[str] = "정보 없음"
    deadline: Optional[str] = "정보 없음"
    contact: Optional[str] = "정보 없음"
    required_documents: Optional[List[str]] = []


@router.post("/validate-image-quality", response_model=ImageQualityResponse)
async def validate_image_quality_endpoint(file: UploadFile = File(...)):
    """
    이미지 품질 사전 검증 (업로드 시점)
    """
    try:
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        handler = get_llm_handler()
        result = await handler.validate_image_quality(base64_image)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-key-info", response_model=KeyInformationResponse)
async def extract_key_information_endpoint(text: str):
    """
    복지 문서 핵심 정보 자동 추출
    """
    try:
        handler = get_llm_handler()
        result = await handler.extract_key_information(text)
        
        # None 값을 기본값으로 변환
        if result is None:
            result = {}
        
        processed_result = {
            "document_type": result.get("document_type") or "알 수 없음",
            "target_audience": result.get("target_audience") or "정보 없음",
            "benefits": result.get("benefits") or [],
            "eligibility": result.get("eligibility") or {},
            "application_method": result.get("application_method") or "정보 없음",
            "deadline": result.get("deadline") or "정보 없음",
            "contact": result.get("contact") or "정보 없음",
            "required_documents": result.get("required_documents") or []
        }
        
        return processed_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"핵심 정보 추출 실패: {str(e)}")


@router.post("/classify-document")
async def classify_document_endpoint(file: UploadFile = File(...)):
    """
    문서 타입 자동 분류
    """
    try:
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        handler = get_llm_handler()
        result = await handler.classify_document_type(base64_image)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-tables")
async def extract_tables_endpoint(file: UploadFile = File(...)):
    """
    표 데이터 구조화 추출
    """
    try:
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        handler = get_llm_handler()
        result = await handler.extract_structured_data(base64_image)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-multiple-pages")
async def process_multiple_pages_endpoint(files: List[UploadFile] = File(...)):
    """
    다중 페이지 문서 통합 처리
    """
    try:
        images = []
        for file in files:
            contents = await file.read()
            base64_image = base64.b64encode(contents).decode('utf-8')
            images.append(base64_image)
        
        handler = get_llm_handler()
        result = await handler.process_multiple_images(images)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))