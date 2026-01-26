import os
import json
import base64
from typing import Dict
import aiofiles
from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
from openai import AsyncAzureOpenAI
from core.config import settings
from agents.human import PromptLoader

# FastAPI 라우터 생성
router = APIRouter()

class LLMHandler:
    """
    Azure OpenAI 통합 핸들러
    - Summarizer: 복지 정보 요약
    - Refiner: 언어 순화
    - Validator: 품질 검증
    - Image OCR: 이미지 텍스트 추출 및 검증
    """
    
    def __init__(self):
        # Azure OpenAI 클라이언트 초기화
        self.client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        
        # 프롬프트 로더 초기화
        self.prompt_loader = PromptLoader()
        
        # 각 에이전트별 시스템 프롬프트 캐싱
        self._system_prompts = {}
    
    async def _load_system_prompt(self, agent_type: str) -> str:
        """
        에이전트별 시스템 프롬프트 로드
        
        Args:
            agent_type: 'summarizer', 'refiner', 'validator'
        """
        if agent_type in self._system_prompts:
            return self._system_prompts[agent_type]
        
        # YAML에서 가이드라인 로드
        guideline = await self.prompt_loader.load(f"{agent_type}.yaml")
        
        # 에이전트별 프롬프트 구축
        if agent_type == "summarizer":
            prompt = self._build_summarizer_prompt(guideline)
        elif agent_type == "refiner":
            prompt = self._build_refiner_prompt(guideline)
        elif agent_type == "validator":
            prompt = self._build_validator_prompt(guideline)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # 캐싱
        self._system_prompts[agent_type] = prompt
        return prompt
    
    def _build_summarizer_prompt(self, guideline: dict) -> str:
        """요약 에이전트 프롬프트 생성"""
        return f"""
<role>
{guideline['role']}
{guideline['objective_persona']}
</role>

<extraction_targets>
추출 우선순위:
- 대상: {guideline['extraction_targets']['target_audience']}
- 혜택: {guideline['extraction_targets']['benefits']}
- 조건: {guideline['extraction_targets']['conditions']}
- 방법: {guideline['extraction_targets']['how_to_apply']}
</extraction_targets>

<execution_rules>
1. {guideline['rules_for_precision']['quantitative_focus']['description']}
   예시: {guideline['rules_for_precision']['quantitative_focus']['example']}
2. {guideline['rules_for_precision']['structural_summary']['description']}
3. {guideline['rules_for_precision']['no_inference']['description']}
</execution_rules>

<constraints>
{chr(10).join([f"- {c}" for c in guideline['constraints']])}
</constraints>

<output_format>
반드시 아래 JSON 구조로만 응답하십시오:
{guideline['output_format']['json_structure']}
</output_format>
""".strip()
    
    def _build_refiner_prompt(self, guideline: dict) -> str:
        """정제 에이전트 프롬프트 생성"""
        return f"""
<role>
{guideline['role']}
{guideline['objective_persona']}
</role>

<rules_by_level>
- Level 13 (초등 6학년): {guideline['rules_by_level']['level_13']['description']}
- Level 7 (유치원): {guideline['rules_by_level']['level_7']['description']}
</rules_by_level>

<constraints>
{chr(10).join([f"- {c}" for c in guideline['constraints']])}
</constraints>

<output_format>
반드시 아래 JSON 구조로만 응답하십시오:
{guideline['output_format']['json_structure']}
</output_format>
""".strip()
    
    def _build_validator_prompt(self, guideline: dict) -> str:
        """검증 에이전트 프롬프트 생성"""
        return f"""
<role>
{guideline['role']}
{guideline['objective_persona']}
</role>

<checkpoints>
1. 팩트 체크: {guideline['validation_checkpoints']['fact_accuracy']}
2. 완전성: {guideline['validation_checkpoints']['completeness']}
3. 중립성: {guideline['validation_checkpoints']['neutrality']}
4. 안전성: {guideline['validation_checkpoints']['safety']}
</checkpoints>

<rules>
- {guideline['rules_for_verification']['binary_judgment']['description']}
- {guideline['rules_for_verification']['evidence_required']['description']}
</rules>

<constraints>
{chr(10).join([f"- {c}" for c in guideline['constraints']])}
</constraints>

<output_format>
Return only the following JSON structure:
{guideline['output_format']['json_structure']}
</output_format>
""".strip()
    
    async def summarize(self, content: str) -> str:
        """
        1단계: 복지 정보 요약
        
        Args:
            content: 요약할 원문
            
        Returns:
            요약된 텍스트
        """
        system_prompt = await self._load_system_prompt("summarizer")
        
        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            temperature=0.3,  # 정확성 중시
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    async def refine(self, content: str, level: int = 13) -> str:
        """
        2단계: 언어 순화 (난이도 조정)
        
        Args:
            content: 순화할 텍스트
            level: 난이도 (7=유치원, 13=초등6학년)
            
        Returns:
            순화된 텍스트
        """
        system_prompt = await self._load_system_prompt("refiner")
        
        user_message = f"""
난이도: Level {level}
처리할 텍스트:
{content}
"""
        
        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.5,  # 창의성 약간 허용
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    
    async def validate(self, original: str, processed: str) -> str:
        """
        3단계: 품질 검증
        
        Args:
            original: 원본 텍스트
            processed: 처리된 텍스트
            
        Returns:
            검증 결과 (JSON 형식)
        """
        system_prompt = await self._load_system_prompt("validator")
        
        user_message = f"""
원문:
{original}

처리된 텍스트:
{processed}

위 두 텍스트를 비교하여 검증해주세요.
"""
        
        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,  # 엄격한 검증
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    async def extract_text_from_image(self, base64_image: str) -> str:
        """
        이미지에서 텍스트 추출 (OCR)
        
        Args:
            base64_image: Base64로 인코딩된 이미지 데이터
            
        Returns:
            추출된 텍스트
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """이미지에서 모든 텍스트를 정확하게 추출해주세요.
                                
규칙:
- 모든 텍스트를 빠짐없이 추출
- 원본 텍스트 그대로 유지 (띄어쓰기, 줄바꿈 포함)
- 텍스트가 없으면 "텍스트 없음"이라고 응답
- 추가 설명 없이 텍스트만 반환"""
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
                temperature=0.1  # 일관성을 위해 낮은 temperature
            )
            
            extracted_text = response.choices[0].message.content.strip()
            return extracted_text
            
        except Exception as e:
            raise Exception(f"텍스트 추출 실패: {str(e)}")
    
    async def verify_extracted_text(self, extracted_text: str, base64_image: str) -> Dict:
        """
        추출된 텍스트 검증
        
        Args:
            extracted_text: 추출된 텍스트
            base64_image: Base64로 인코딩된 원본 이미지
            
        Returns:
            검증 결과 딕셔너리
            {
                "is_valid": bool,
                "confidence_score": int (0-100),
                "issues": List[str],
                "corrected_text": str (필요시)
            }
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""다음 텍스트가 이미지에서 정확하게 추출되었는지 검증해주세요.

추출된 텍스트:
{extracted_text}

검증 기준:
1. 모든 텍스트가 포함되었는가?
2. 텍스트 순서가 정확한가?
3. 오타나 누락이 있는가?

JSON 형식으로 응답:
{{
    "is_valid": true/false,
    "confidence_score": 0-100,
    "issues": ["발견된 문제점들"],
    "corrected_text": "수정된 텍스트 (필요시)"
}}"""
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
                temperature=0.1,
                response_format={"type": "json_object"}  # JSON 형식 강제
            )
            
            verification_result = json.loads(response.choices[0].message.content)
            return verification_result
            
        except Exception as e:
            raise Exception(f"텍스트 검증 실패: {str(e)}")


# 싱글톤 인스턴스 (선택사항)
_llm_handler_instance = None

def get_llm_handler() -> LLMHandler:
    """LLM 핸들러 싱글톤 인스턴스 반환"""
    global _llm_handler_instance
    if _llm_handler_instance is None:
        _llm_handler_instance = LLMHandler()
    return _llm_handler_instance

# ============= API 엔드포인트 정의 =============

class ImageUploadResponse(BaseModel):
    extracted_text: str
    verification: Dict

class TextProcessRequest(BaseModel):
    text: str
    level: int = 13


@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_and_extract_image(file: UploadFile = File(...)):
    """
    이미지 업로드 및 텍스트 추출
    """
    try:
        # 이미지 읽기
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        # LLM 핸들러 가져오기
        handler = get_llm_handler()
        
        # 텍스트 추출
        extracted_text = await handler.extract_text_from_image(base64_image)
        
        # 텍스트 검증
        verification = await handler.verify_extracted_text(extracted_text, base64_image)
        
        return {
            "extracted_text": extracted_text,
            "verification": verification
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize")
async def summarize_text(request: TextProcessRequest):
    """
    텍스트 요약
    """
    try:
        handler = get_llm_handler()
        result = await handler.summarize(request.text)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine")
async def refine_text(request: TextProcessRequest):
    """
    텍스트 순화
    """
    try:
        handler = get_llm_handler()
        result = await handler.refine(request.text, request.level)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_text(original: str, processed: str):
    """
    텍스트 검증
    """
    try:
        handler = get_llm_handler()
        result = await handler.validate(original, processed)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))