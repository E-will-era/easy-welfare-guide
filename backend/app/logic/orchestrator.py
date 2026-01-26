from app.agents.llm_handler import LLMHandler, get_llm_handler
from app.core.logger import logger
from typing import Optional

class WelfareOrchestrator:
    """
    복지 정보 처리 파이프라인 오케스트레이터
    
    3단계 처리 흐름:
    1. Summarize: 복지 정보 요약
    2. Refine: 언어 순화 (난이도 조정)
    3. Validate: 품질 검증
    """
    
    def __init__(self):
        # LLM 핸들러 초기화 (싱글톤)
        self.llm_handler = get_llm_handler()
        logger.info("WelfareOrchestrator initialized")
    
    async def process(
        self, 
        content: str, 
        level: int = 13,
        skip_validation: bool = False
    ) -> str:
        """
        전체 파이프라인 실행
        
        Args:
            content: 처리할 원문
            level: 난이도 (7=유치원, 13=초등6학년)
            skip_validation: 검증 단계 생략 여부
            
        Returns:
            최종 처리된 텍스트
        """
        logger.info(f"Starting welfare guide processing pipeline (level={level})")
        
        try:
            # 1단계: 요약
            logger.info("Step 1/3: Summarizing...")
            summary = await self.summarize(content)
            logger.debug(f"Summary result: {summary[:100]}...")
            
            # 2단계: 언어 순화
            logger.info(f"Step 2/3: Refining to level {level}...")
            refined = await self.refine(summary, level)
            logger.debug(f"Refined result: {refined[:100]}...")
            
            # 3단계: 검증 (선택사항)
            if not skip_validation:
                logger.info("Step 3/3: Validating...")
                validation = await self.validate(content, refined)
                logger.debug(f"Validation result: {validation[:100]}...")
                
                # 검증 결과 로깅 (실제로는 파싱해서 처리)
                logger.info("Validation completed")
            
            logger.info("Pipeline completed successfully")
            return refined
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            raise
    
    async def summarize(self, content: str) -> str:
        """
        1단계: 복지 정보 요약
        
        Args:
            content: 요약할 원문
            
        Returns:
            요약된 텍스트
        """
        try:
            result = await self.llm_handler.summarize(content)
            logger.info("Summarization completed")
            return result
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            raise Exception(f"요약 중 오류 발생: {str(e)}")
    
    async def refine(self, content: str, level: int = 13) -> str:
        """
        2단계: 언어 순화
        
        Args:
            content: 순화할 텍스트
            level: 난이도 (7 또는 13)
            
        Returns:
            순화된 텍스트
        """
        # 레벨 검증
        if level not in [7, 13]:
            logger.warning(f"Invalid level {level}, defaulting to 13")
            level = 13
        
        try:
            result = await self.llm_handler.refine(content, level)
            logger.info(f"Refinement completed (level={level})")
            return result
        except Exception as e:
            logger.error(f"Refinement failed: {str(e)}")
            raise Exception(f"언어 순화 중 오류 발생: {str(e)}")
    
    async def validate(self, original: str, processed: str) -> str:
        """
        3단계: 품질 검증
        
        Args:
            original: 원본 텍스트
            processed: 처리된 텍스트
            
        Returns:
            검증 결과 (JSON 형식)
        """
        try:
            result = await self.llm_handler.validate(original, processed)
            logger.info("Validation completed")
            return result
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            raise Exception(f"검증 중 오류 발생: {str(e)}")
    
    async def process_with_rag(
        self, 
        query: str,
        level: int = 13
    ) -> str:
        """
        RAG 연동 파이프라인 (향후 확장)
        
        Args:
            query: 사용자 질의
            level: 난이도
            
        Returns:
            최종 처리된 텍스트
        """
        logger.info(f"Starting RAG-enabled pipeline for query: {query[:50]}...")
        
        # TODO: RAG 모듈 연동
        # docs = await rag_service.search(query)
        # content = self._combine_docs(docs)
        
        # 임시: 쿼리를 그대로 사용
        content = query
        
        return await self.process(content, level)
    
    def _combine_docs(self, docs: list) -> str:
        """
        RAG 검색 결과를 하나의 텍스트로 결합
        
        Args:
            docs: 검색된 문서 리스트
            
        Returns:
            결합된 텍스트
        """
        # TODO: 실제 RAG 결과 처리 로직
        return "\n\n".join([doc.get("content", "") for doc in docs])


# 싱글톤 인스턴스 (선택사항)
_orchestrator_instance: Optional[WelfareOrchestrator] = None

def get_orchestrator() -> WelfareOrchestrator:
    """WelfareOrchestrator 싱글톤 인스턴스 반환"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = WelfareOrchestrator()
    return _orchestrator_instance