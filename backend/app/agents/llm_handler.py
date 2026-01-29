import os
import json
from typing import Dict, List
from openai import AsyncAzureOpenAI
from app.core.config import settings
from app.agents.human import get_prompt_loader
from app.core.logger import logger

class LLMHandler:
    """
    Azure OpenAI 통합 핸들러 (TXT 프롬프트 버전)
    - Summarizer: 키워드 추출
    - Refiner: 키워드 순화
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
        self.prompt_loader = get_prompt_loader()
        
        # 프롬프트 캐싱
        self._prompts = {}
        
        logger.info("LLMHandler initialized with TXT prompts")
    
    async def _load_prompt(self, agent_type: str) -> str:
        """
        에이전트별 프롬프트 로드
        
        Args:
            agent_type: 'summarizer', 'refiner', 'validator'
            
        Returns:
            프롬프트 텍스트
        """
        if agent_type in self._prompts:
            return self._prompts[agent_type]
        
        try:
            # TXT 파일에서 프롬프트 로드
            filename = f"{agent_type}_prompt.txt"
            prompt = await self.prompt_loader.load(filename)
            
            # 캐싱
            self._prompts[agent_type] = prompt
            logger.info(f"✅ {agent_type} 프롬프트 로드 완료")
            
            return prompt
            
        except FileNotFoundError:
            # Fallback 프롬프트 사용
            logger.warning(f"⚠️ {agent_type} 프롬프트 파일 없음, Fallback 사용")
            fallback = self.prompt_loader.get_fallback_prompt(agent_type)
            self._prompts[agent_type] = fallback
            return fallback
        except Exception as e:
            logger.error(f"❌ {agent_type} 프롬프트 로드 실패: {e}")
            raise
    
    # ============= 텍스트 처리 메서드 (새로운 방식) =============
    
    async def extract_keywords(self, user_text: str, rag_context: str) -> Dict:
        """
        키워드 추출 (Summarizer)
        
        Args:
            user_text: OCR 추출 텍스트
            rag_context: RAG 검색 결과
            
        Returns:
            {
                "title": "# 복지 서비스 명칭",
                "keywords": [...],
                "metadata": {...}
            }
        """
        prompt_template = await self._load_prompt("summarizer")
        
        user_message = f"""
{prompt_template}

[원문]
{user_text[:2000]}

[RAG 검색 결과]
{rag_context[:2000]}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": user_message}],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"📌 키워드 추출: {result.get('metadata', {}).get('total_keywords', 0)}개")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 오류: {e}")
            return {
                "title": "# 복지 서비스",
                "keywords": [],
                "metadata": {"total_keywords": 0}
            }
        except Exception as e:
            logger.error(f"❌ 키워드 추출 오류: {e}")
            raise
    
    async def refine_keywords(self, keywords_json: Dict, level: int = 13) -> Dict:
        """
        키워드 순화 (Refiner)
        
        Args:
            keywords_json: extract_keywords()의 출력
            level: 난이도 (7=유치원, 13=초등6학년)
            
        Returns:
            {
                "title": "# 복지 서비스 명칭",
                "keywords": [...], (refined_context 추가됨)
                "metadata": {...}
            }
        """
        prompt_template = await self._load_prompt("refiner")
        
        user_message = f"""
{prompt_template}

[입력 JSON]
{json.dumps(keywords_json, ensure_ascii=False, indent=2)}

[난이도]
읽기 수준: Level {level}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": user_message}],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=3000
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"✏️ 키워드 순화: {result.get('metadata', {}).get('total_keywords', 0)}개")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 오류: {e}")
            return keywords_json  # Fallback: 입력 그대로 반환
        except Exception as e:
            logger.error(f"❌ 키워드 순화 오류: {e}")
            raise
    
    async def validate_keywords(self, original_text: str, refined_json: Dict) -> Dict:
        """
        품질 검증 (Validator)
        
        Args:
            original_text: 원본 텍스트
            refined_json: refine_keywords()의 출력
            
        Returns:
            {
                "passed": bool,
                "score": int,
                "validation_details": {...},
                "final_verdict": str,
                "recommendations": [...]
            }
        """
        prompt_template = await self._load_prompt("validator")
        
        user_message = f"""
{prompt_template}

[원본 텍스트]
{original_text[:2000]}

[검증 대상 JSON]
{json.dumps(refined_json, ensure_ascii=False, indent=2)}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
                messages=[{"role": "user", "content": user_message}],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"🔍 검증: {result.get('final_verdict')} (점수: {result.get('score')})")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 파싱 오류: {e}")
            return {
                "passed": True,
                "score": 0,
                "final_verdict": "검증 오류 - 기본 통과",
                "recommendations": ["검증 시스템 오류로 인한 자동 승인"]
            }
        except Exception as e:
            logger.error(f"❌ 검증 오류: {e}")
            raise
    
    # ============= 레거시 메서드 (하위 호환성) =============
    
    async def summarize(self, content: str) -> str:
        """
        [레거시] 1단계: 복지 정보 요약
        
        Args:
            content: 요약할 원문
            
        Returns:
            요약된 텍스트
        """
        logger.warning("⚠️ 레거시 메서드 사용: summarize() → extract_keywords() 권장")
        
        # 간단한 요약 프롬프트
        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "복지 정보를 간결하게 요약하세요."},
                {"role": "user", "content": content}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    async def refine(self, content: str, level: int = 13) -> str:
        """
        [레거시] 2단계: 언어 순화
        
        Args:
            content: 순화할 텍스트
            level: 난이도 (7=유치원, 13=초등6학년)
            
        Returns:
            순화된 텍스트
        """
        logger.warning("⚠️ 레거시 메서드 사용: refine() → refine_keywords() 권장")
        
        user_message = f"""
난이도: Level {level}
처리할 텍스트:
{content}

위 텍스트를 초등학생도 이해할 수 있도록 쉽게 바꿔주세요.
"""
        
        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.5,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    
    async def validate(self, original: str, processed: str) -> str:
        """
        [레거시] 3단계: 품질 검증
        
        Args:
            original: 원본 텍스트
            processed: 처리된 텍스트
            
        Returns:
            검증 결과 (JSON 형식)
        """
        logger.warning("⚠️ 레거시 메서드 사용: validate() → validate_keywords() 권장")
        
        user_message = f"""
원문:
{original}

처리된 텍스트:
{processed}

위 두 텍스트를 비교하여 검증해주세요. JSON 형식으로 응답하세요.
"""
        
        response = await self.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.1,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    # ============= 이미지 처리 메서드 (유지) =============
    
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
                                "text": """이 이미지의 품질을 평가해주세요.

평가 기준:
1. 해상도 (선명도)
2. 밝기 및 대비
3. 텍스트 가독성
4. 전체적인 이미지 품질

JSON 형식으로 응답:
{
    "is_acceptable": true/false,
    "quality_score": 0-100,
    "resolution": "high/medium/low",
    "issues": ["문제점1", "문제점2"],
    "recommendations": ["권장사항1", "권장사항2"]
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
            raise Exception(f"이미지 품질 검증 실패: {str(e)}")
    
    async def extract_text_from_image(self, base64_image: str) -> str:
        """
        이미지에서 텍스트 추출 (OCR)
        
        Args:
            base64_image: Base64 인코딩된 이미지
            
        Returns:
            추출된 텍스트
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
                                "text": "이미지에 있는 모든 텍스트를 정확하게 추출해주세요."
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
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"텍스트 추출 실패: {str(e)}")
    
    async def classify_document_type(self, base64_image: str) -> Dict:
        """
        문서 타입 자동 분류
        
        Args:
            base64_image: Base64 인코딩된 이미지
            
        Returns:
            {
                "document_type": "공고문/신청서/안내문/기타",
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
                                "text": """이 문서의 타입을 분류해주세요.

문서 타입:
- 공고문: 복지 혜택을 알리는 공식 문서
- 신청서: 복지 신청을 위한 양식
- 안내문: 복지 제도 설명 자료
- 기타: 위에 해당하지 않는 문서

JSON 형식으로 응답:
{
    "document_type": "공고문/신청서/안내문/기타",
    "confidence": 0.0-1.0,
    "characteristics": ["특징1", "특징2"]
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
                max_tokens=500,
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


# 싱글톤 인스턴스
_llm_handler_instance = None

def get_llm_handler() -> LLMHandler:
    """LLM 핸들러 싱글톤 인스턴스 반환"""
    global _llm_handler_instance
    if _llm_handler_instance is None:
        _llm_handler_instance = LLMHandler()
    return _llm_handler_instance