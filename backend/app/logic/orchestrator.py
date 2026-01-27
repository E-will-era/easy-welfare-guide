"""
Welfare Orchestrator - 비즈니스 로직 처리
복지 정보 처리 파이프라인 관리
"""
from typing import Dict
from app.agents.llm_handler import get_llm_handler
from app.core.config import settings


class WelfareOrchestrator:
    """
    복지 정보 처리 오케스트레이터
    
    처리 단계:
    1. 텍스트 추출 (OCR)
    2. 복지 관련성 검증
    3. 요약
    4. 순화어 변환 (13세 수준)
    5. 검증
    """
    
    def __init__(self):
        self.llm_handler = get_llm_handler()
    
    
    async def extract_text_from_image(self, base64_image: str) -> str:
        """
        이미지에서 텍스트 추출 (OCR)
        
        Args:
            base64_image: base64 인코딩된 이미지
            
        Returns:
            추출된 텍스트
        """
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "이미지의 모든 텍스트를 정확하게 추출하세요. 텍스트만 반환하고 다른 설명은 추가하지 마세요."
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
        
        extracted_text = response.choices[0].message.content.strip()
        return extracted_text
    
    
    async def check_welfare_relevance(self, text: str) -> bool:
        """
        복지 관련 문서인지 판단
        
        Args:
            text: 검증할 텍스트
            
        Returns:
            복지 관련 여부 (True/False)
        """
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """다음 텍스트가 복지 관련 문서인지 판단하세요.

복지 관련 키워드:
- 지원, 혜택, 신청, 보조금, 수당, 복지
- 청년, 주거, 교육, 의료, 돌봄
- 자격, 조건, 대상, 기준, 소득
- 신청서, 안내문, 공고

'yes' 또는 'no'로만 답하세요."""
                },
                {
                    "role": "user",
                    "content": text[:1000]  # 앞부분 1000자만 검증
                }
            ],
            max_tokens=10,
            temperature=0.0
        )
        
        result = response.choices[0].message.content.strip().lower()
        return result == "yes"
    
    
    async def summarize(self, content: str) -> str:
        """
        복지 정보 요약
        
        Args:
            content: 요약할 원문
            
        Returns:
            요약된 내용 (행정 용어 유지)
        """
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """다음 복지 공고문을 핵심 정보만 간단히 요약하세요.

반드시 포함할 정보:
- 신청 가능 여부 및 기간
- 소득 기준 (중위소득 등)
- 지원 대상 (나이, 조건)
- 지원 내용 (금액, 혜택)
- 필요 서류

간결하게 작성하되, 중요한 수치와 조건은 정확하게 포함하세요."""
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    
    async def refine(self, content: str) -> str:
        """
        행정/복지 용어를 순화어로 변환 (13세 = 초등 6학년 수준)
        
        Args:
            content: 변환할 내용
            
        Returns:
            순화된 내용
        """
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """다음 텍스트를 초등학교 6학년(13세)이 이해할 수 있는 쉬운 말로 바꾸세요.

변환 예시:
- 중위소득 → 평균적인 가정의 소득
- 근로장려금 → 일하는 사람을 돕는 지원금
- 보조금 → 나라에서 도와주는 돈
- 부양가족 → 함께 사는 가족
- 소득 기준 → 벌어들이는 돈의 기준
- 신청 자격 → 신청할 수 있는 조건
- 지원 대상 → 도움을 받을 수 있는 사람

내용과 구조는 그대로 유지하고, 어려운 단어만 쉽게 바꾸세요."""
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    
    
    async def validate(self, original: str, summary: str) -> Dict:
        """
        요약 내용 검증
        - Fact Check: 원본과 요약이 일치하는지 (환각 없음)
        - Omission Check: 중요한 정보가 누락되지 않았는지
        
        Args:
            original: 원본 텍스트
            summary: 순화된 요약 텍스트
            
        Returns:
            {"passed": bool, "fact_check": bool, "omission_check": bool}
        """
        response = await self.llm_handler.client.chat.completions.create(
            model=settings.AZURE_OPENAI_API_DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """원본 텍스트와 요약을 비교하여 검증하세요.

검증 항목:
1. Fact Check: 요약 내용이 원본과 일치하는가?
   - 금액, 날짜, 조건이 정확한가?
   - 사실이 왜곡되지 않았는가?

2. Omission Check: 중요한 정보가 누락되지 않았는가?
   - 신청 기간, 대상, 금액 등 필수 정보 포함 여부

검증 결과만 'passed' 또는 'failed'로 답하세요."""
                },
                {
                    "role": "user",
                    "content": f"원본:\n{original[:2000]}\n\n요약:\n{summary}"
                }
            ],
            max_tokens=20,
            temperature=0.0
        )
        
        result = response.choices[0].message.content.strip().lower()
        passed = result == "passed"
        
        return {
            "passed": passed,
            "fact_check": passed,
            "omission_check": passed
        }