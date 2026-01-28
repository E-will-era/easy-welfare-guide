import os
import json
import aiofiles
from typing import Dict, List
from openai import AsyncAzureOpenAI
from app.core.config import settings
from app.agents.human import PromptLoader

class LLMHandler:
    """
    Azure OpenAI 통합 핸들러
    - Summarizer: 복지 정보 요약
    - Refiner: 언어 순화
    - Validator: 품질 검증
    - Image Processing: 이미지 기반 문서 처리
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
    
    # ============= 텍스트 처리 메서드 =============
    
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
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
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
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
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
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,  # 엄격한 검증
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    # ============= 이미지 처리 메서드 =============
    
    async def validate_image_quality(self, base64_image: str) -> Dict:
        """
        이미지 업로드 시점에 품질 검증
        
        Args:
            base64_image: Base64 인코딩된 이미지
            
        Returns:
            {
                "is_acceptable": bool,
                "quality_score": int (0-100),
                "resolution": str,
                "issues": List[str],
                "recommendations": List[str]
            }
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """이 이미지의 품질을 평가하고 텍스트 추출 가능성을 판단해주세요.

검증 항목:
1. 해상도 - 텍스트가 선명하게 보이는가?
2. 조명 - 너무 어둡거나 밝지 않은가?
3. 초점 - 텍스트가 흐릿하지 않은가?
4. 회전/기울기 - 문서가 바르게 정렬되어 있는가?
5. 텍스트 존재 - 추출할 텍스트가 있는가?

JSON 형식으로 응답:
{
    "is_acceptable": true/false,
    "quality_score": 0-100,
    "resolution": "고해상도/중간/저해상도",
    "issues": ["발견된 문제점들"],
    "recommendations": ["개선 방법들"]
}"""
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
                max_tokens=1000,
                temperature=0.1
            )
            
            # JSON 파싱
            content = response.choices[0].message.content
            # Markdown 코드 블록 제거
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            raise Exception(f"이미지 품질 검증 실패: {str(e)}")
    
    async def extract_key_information(self, text: str) -> Dict:
        """
        복지 문서에서 핵심 정보 자동 추출
        
        Args:
            text: OCR로 추출된 텍스트
            
        Returns:
            {
                "document_type": str,
                "target_audience": str,
                "benefits": List[str],
                "eligibility": Dict,
                "application_method": str,
                "deadline": str,
                "contact": str,
                "required_documents": List[str]
            }
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": """당신은 복지 문서에서 핵심 정보를 추출하는 전문가입니다.
다음 정보를 정확하게 파싱하세요:
- 문서 유형 (공고문/신청서/안내문)
- 지원 대상
- 혜택 내용
- 자격 조건 (소득, 나이 등)
- 신청 방법
- 신청 기한
- 문의처
- 제출 서류"""
                    },
                    {
                        "role": "user",
                        "content": f"""다음 복지 문서에서 핵심 정보를 추출해주세요:

{text}

JSON 형식으로 응답:
{{
    "document_type": "공고문/신청서/안내문/기타",
    "target_audience": "지원 대상 요약",
    "benefits": ["혜택1", "혜택2"],
    "eligibility": {{
        "income": "소득 조건",
        "age": "나이 조건",
        "other": "기타 조건"
    }},
    "application_method": "신청 방법",
    "deadline": "신청 기한",
    "contact": "문의처",
    "required_documents": ["서류1", "서류2"]
}}

정보가 없으면 null로 표시하세요."""
                    }
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            # JSON 파싱
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            raise Exception(f"핵심 정보 추출 실패: {str(e)}")
    
    async def classify_document_type(self, base64_image: str) -> Dict:
        """
        문서 타입 자동 분류
        
        Args:
            base64_image: Base64 인코딩된 이미지
            
        Returns:
            {
                "document_type": str,
                "confidence": float,
                "characteristics": List[str]
            }
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """이 문서의 유형을 분류해주세요.

분류 기준:
- 공고문: 복지 제도 안내, 공지 형식
- 신청서: 신청인 정보 입력 양식
- 안내문: 상세 절차 설명
- 증빙서류: 소득증명, 주민등록등본 등
- 기타: 위에 해당하지 않음

JSON 형식으로 응답:
{
    "document_type": "공고문/신청서/안내문/증빙서류/기타",
    "confidence": 0.0-1.0,
    "characteristics": ["이 분류의 근거들"]
}"""
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
                max_tokens=800,
                temperature=0.1
            )
            
            # JSON 파싱
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            raise Exception(f"문서 타입 분류 실패: {str(e)}")
    
    async def extract_structured_data(self, base64_image: str) -> Dict:
        """
        테이블/표 형태 데이터를 구조화된 JSON으로 변환
        
        Args:
            base64_image: Base64 인코딩된 이미지
            
        Returns:
            {
                "tables": List[Dict],
                "has_tables": bool,
                "table_count": int
            }
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """이미지에서 표(테이블) 데이터를 추출하여 JSON으로 변환해주세요.

변환 규칙:
1. 각 표를 별도의 객체로 분리
2. 헤더와 데이터 행 구분
3. 수치 데이터는 숫자로, 텍스트는 문자열로

JSON 형식:
{
    "has_tables": true/false,
    "table_count": 숫자,
    "tables": [
        {
            "title": "표 제목",
            "headers": ["헤더1", "헤더2"],
            "rows": [
                {"헤더1": "값1", "헤더2": "값2"},
                ...
            ]
        }
    ]
}

표가 없으면 has_tables: false, tables: []로 응답"""
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
                max_tokens=2500,
                temperature=0.1
            )
            
            # JSON 파싱
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            raise Exception(f"구조화 데이터 추출 실패: {str(e)}")
    
    async def process_multiple_images(self, images: List[str]) -> Dict:
        """
        여러 페이지 문서 통합 처리
        
        Args:
            images: Base64 인코딩된 이미지 리스트
            
        Returns:
            {
                "combined_text": str,
                "page_count": int,
                "page_order": List[int]
            }
        """
        try:
            # 각 이미지에서 텍스트 추출 (간단한 OCR)
            extracted_texts = []
            for idx, img in enumerate(images):
                # 여기서는 간단히 각 이미지를 Vision API로 처리
                response = await self.client.chat.completions.create(
                    model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "이 이미지에서 모든 텍스트를 추출해주세요."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.1
                )
                
                text = response.choices[0].message.content
                extracted_texts.append({
                    "page": idx + 1,
                    "text": text
                })
            
            # 페이지 순서 자동 정렬 및 통합
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "여러 페이지의 텍스트를 논리적 순서로 정렬하고 통합하세요."
                    },
                    {
                        "role": "user",
                        "content": f"""다음 페이지들을 올바른 순서로 정렬하고 통합해주세요:

{json.dumps(extracted_texts, ensure_ascii=False, indent=2)}

JSON 형식으로 응답:
{{
    "combined_text": "통합된 전체 텍스트",
    "page_count": {len(images)},
    "page_order": [정렬된 페이지 번호들],
    "rationale": "정렬 근거"
}}"""
                    }
                ],
                max_tokens=3000,
                temperature=0.2
            )
            
            # JSON 파싱
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            raise Exception(f"다중 이미지 처리 실패: {str(e)}")
    
    async def validate_with_feedback(
        self, 
        extracted_text: str, 
        base64_image: str
    ) -> Dict:
        """
        검증 + 개선 제안
        
        Args:
            extracted_text: 추출된 텍스트
            base64_image: 원본 이미지
            
        Returns:
            {
                "is_valid": bool,
                "confidence_score": int,
                "issues": List[Dict],
                "feedback": Dict
            }
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""다음 텍스트가 이미지에서 정확하게 추출되었는지 검증하고,
문제가 있다면 구체적인 개선 방법을 제시해주세요.

추출된 텍스트:
{extracted_text}

JSON 형식으로 응답:
{{
    "is_valid": true/false,
    "confidence_score": 0-100,
    "issues": [
        {{
            "type": "누락/오타/순서오류/기타",
            "location": "문제가 발생한 위치",
            "description": "구체적 설명"
        }}
    ],
    "feedback": {{
        "user_action": "사용자가 해야 할 조치",
        "technical_issue": "기술적 문제점",
        "retry_recommended": true/false
    }}
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
                max_tokens=1500,
                temperature=0.1
            )
            
            # JSON 파싱
            content = response.choices[0].message.content
            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
        except Exception as e:
            raise Exception(f"피드백 검증 실패: {str(e)}")


# 싱글톤 인스턴스 (선택사항)
_llm_handler_instance = None

def get_llm_handler() -> LLMHandler:
    """LLM 핸들러 싱글톤 인스턴스 반환"""
    global _llm_handler_instance
    if _llm_handler_instance is None:
        _llm_handler_instance = LLMHandler()
    return _llm_handler_instance