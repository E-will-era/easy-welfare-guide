import os
from pathlib import Path
from typing import Dict, Optional
from app.core.logger import logger

"""
파일명: human.py
설명: TXT 프롬프트 파일 로더 (기존 human.py를 TXT 방식으로 전환)
"""

class PromptLoader:
    """
    TXT 프롬프트 파일 로더
    - Summarizer, Refiner, Validator의 TXT 프롬프트 로드
    - 캐싱으로 성능 최적화
    """
    
    def __init__(self):
        # prompts 폴더 경로 설정
        backend_dir = Path(__file__).parent
        self.prompts_dir = backend_dir / "prompts"
        
        # 캐시 저장소
        self._cache: Dict[str, str] = {}
        
        logger.info(f"PromptLoader initialized. Prompts directory: {self.prompts_dir}")
    
    async def load(self, filename: str) -> str:
        """
        TXT 프롬프트 파일 비동기 로드
        
        Args:
            filename: TXT 파일명 (예: 'summarizer_prompt.txt', 'refiner_prompt.txt')
            
        Returns:
            프롬프트 텍스트 문자열
            
        Raises:
            FileNotFoundError: 파일이 없을 때
        """
        # 캐시 확인
        if filename in self._cache:
            logger.debug(f"Loading from cache: {filename}")
            return self._cache[filename]
        
        # 파일 경로 생성
        file_path = self.prompts_dir / filename
        
        if not file_path.exists():
            error_msg = f"프롬프트 파일을 찾을 수 없습니다: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            # 동기 파일 읽기 (TXT는 가볍기 때문에 동기로 충분)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 캐싱
            self._cache[filename] = content
            logger.info(f"Successfully loaded prompt: {filename}")
            
            return content
            
        except Exception as e:
            error_msg = f"파일 읽기 오류 ({filename}): {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def load_sync(self, filename: str) -> str:
        """
        TXT 프롬프트 파일 동기 로드
        
        Args:
            filename: TXT 파일명
            
        Returns:
            프롬프트 텍스트 문자열
        """
        # 캐시 확인
        if filename in self._cache:
            return self._cache[filename]
        
        file_path = self.prompts_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self._cache[filename] = content
            return content
            
        except Exception as e:
            raise Exception(f"파일 읽기 오류 ({filename}): {str(e)}")
    
    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        logger.info("Prompt cache cleared")
    
    def get_cache_info(self) -> Dict[str, int]:
        """캐시 정보 반환"""
        return {
            "cached_files": len(self._cache),
            "files": list(self._cache.keys())
        }
    
    def get_fallback_prompt(self, prompt_type: str) -> str:
        """
        프롬프트 파일이 없을 때 사용할 기본 프롬프트
        
        Args:
            prompt_type: 'summarizer', 'refiner', 'validator'
            
        Returns:
            기본 프롬프트 문자열
        """
        fallbacks = {
            'summarizer': """당신은 복지 문서에서 어려운 키워드를 추출하는 전문가입니다.
개념적 키워드를 우선 추출하고, 단편적 정보(날짜, URL)는 제외하세요.
반드시 JSON 형식으로만 응답하세요.""",
            
            'refiner': """당신은 어려운 키워드를 초등 6학년 수준으로 순화하는 전문가입니다.
숫자는 절대 변경하지 말고, 개념의 핵심 의미를 보존하세요.
반드시 JSON 형식으로만 응답하세요.""",
            
            'validator': """당신은 키워드와 순화 결과를 검증하는 전문가입니다.
숫자 정확성, 개념 보존, 마크다운 형식을 확인하세요.
반드시 JSON 형식으로만 응답하세요."""
        }
        
        return fallbacks.get(prompt_type, '프롬프트를 찾을 수 없습니다.')


# 싱글톤 인스턴스
_prompt_loader_instance: Optional[PromptLoader] = None

def get_prompt_loader() -> PromptLoader:
    """PromptLoader 싱글톤 인스턴스 반환"""
    global _prompt_loader_instance
    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()
    return _prompt_loader_instance


# 테스트 코드
if __name__ == "__main__":
    import asyncio
    
    async def test_loader():
        loader = PromptLoader()
        
        print("=== PromptLoader 테스트 ===\n")
        
        # 1. Summarizer 로드
        try:
            summarizer = await loader.load("summarizer_prompt.txt")
            print(f"✅ Summarizer 로드 성공 (길이: {len(summarizer)} 문자)")
            print(f"   첫 50자: {summarizer[:50]}...")
        except Exception as e:
            print(f"❌ Summarizer 로드 실패: {e}")
        
        # 2. Refiner 로드
        try:
            refiner = await loader.load("refiner_prompt.txt")
            print(f"✅ Refiner 로드 성공 (길이: {len(refiner)} 문자)")
            print(f"   첫 50자: {refiner[:50]}...")
        except Exception as e:
            print(f"❌ Refiner 로드 실패: {e}")
        
        # 3. Validator 로드
        try:
            validator = await loader.load("validator_prompt.txt")
            print(f"✅ Validator 로드 성공 (길이: {len(validator)} 문자)")
            print(f"   첫 50자: {validator[:50]}...")
        except Exception as e:
            print(f"❌ Validator 로드 실패: {e}")
        
        # 4. 캐시 정보
        print(f"\n📦 캐시 정보: {loader.get_cache_info()}")
        
        # 5. Fallback 테스트
        print(f"\n🔄 Fallback 프롬프트:")
        print(f"   Summarizer: {loader.get_fallback_prompt('summarizer')[:50]}...")
    
    # 비동기 실행
    asyncio.run(test_loader())