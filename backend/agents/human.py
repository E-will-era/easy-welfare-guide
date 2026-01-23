import os
import yaml
import aiofiles
from pathlib import Path
from typing import Dict, Optional
from backend.core.logger import logger

class PromptLoader:
    """
    YAML 프롬프트 파일 로더
    - Summarizer, Refiner, Validator의 YAML 가이드라인 로드
    - 캐싱으로 성능 최적화
    """
    
    def __init__(self):
        # prompts 폴더 경로 설정
        backend_dir = Path(__file__).parent.parent
        self.prompts_dir = backend_dir / "prompts"
        
        # 캐시 저장소
        self._cache: Dict[str, dict] = {}
        
        logger.info(f"PromptLoader initialized. Prompts directory: {self.prompts_dir}")
    
    async def load(self, filename: str) -> dict:
        """
        YAML 프롬프트 파일 비동기 로드
        
        Args:
            filename: YAML 파일명 (예: 'summarizer.yaml', 'refiner.yaml')
            
        Returns:
            YAML 내용을 딕셔너리로 반환
            
        Raises:
            FileNotFoundError: 파일이 없을 때
            yaml.YAMLError: YAML 파싱 오류
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
            # 비동기 파일 읽기
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                data = yaml.safe_load(content)
            
            # 캐싱
            self._cache[filename] = data
            logger.info(f"Successfully loaded prompt: {filename}")
            
            return data
            
        except yaml.YAMLError as e:
            error_msg = f"YAML 파싱 오류 ({filename}): {str(e)}"
            logger.error(error_msg)
            raise yaml.YAMLError(error_msg)
        except Exception as e:
            error_msg = f"파일 읽기 오류 ({filename}): {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def load_sync(self, filename: str) -> dict:
        """
        YAML 프롬프트 파일 동기 로드 (테스트용)
        
        Args:
            filename: YAML 파일명
            
        Returns:
            YAML 내용을 딕셔너리로 반환
        """
        # 캐시 확인
        if filename in self._cache:
            return self._cache[filename]
        
        file_path = self.prompts_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self._cache[filename] = data
            return data
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"YAML 파싱 오류 ({filename}): {str(e)}")
    
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


# 싱글톤 인스턴스 (선택사항)
_prompt_loader_instance: Optional[PromptLoader] = None

def get_prompt_loader() -> PromptLoader:
    """PromptLoader 싱글톤 인스턴스 반환"""
    global _prompt_loader_instance
    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()
    return _prompt_loader_instance


# 하위 호환성을 위한 함수들 (기존 코드와 호환)
def get_human_guideline(filename: str = "summarizer.yaml") -> Optional[dict]:
    """
    레거시 함수 - 하위 호환성 유지
    
    Args:
        filename: YAML 파일명
        
    Returns:
        YAML 데이터 또는 None
    """
    try:
        loader = get_prompt_loader()
        return loader.load_sync(filename)
    except Exception as e:
        logger.error(f"Failed to load guideline: {str(e)}")
        return None


# 테스트 코드
if __name__ == "__main__":
    import asyncio
    
    async def test_loader():
        loader = PromptLoader()
        
        print("=== PromptLoader 테스트 ===\n")
        
        # 1. Summarizer 로드
        try:
            summarizer = await loader.load("summarizer.yaml")
            print(f"✅ Summarizer 로드 성공: {summarizer.get('agent_name')}")
        except Exception as e:
            print(f"❌ Summarizer 로드 실패: {e}")
        
        # 2. Refiner 로드
        try:
            refiner = await loader.load("refiner.yaml")
            print(f"✅ Refiner 로드 성공: {refiner.get('agent_name')}")
        except Exception as e:
            print(f"❌ Refiner 로드 실패: {e}")
        
        # 3. Validator 로드
        try:
            validator = await loader.load("validator.yaml")
            print(f"✅ Validator 로드 성공: {validator.get('agent_name')}")
        except Exception as e:
            print(f"❌ Validator 로드 실패: {e}")
        
        # 4. 캐시 정보
        print(f"\n📦 캐시 정보: {loader.get_cache_info()}")
    
    # 비동기 실행
    asyncio.run(test_loader())