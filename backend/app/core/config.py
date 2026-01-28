import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """
    애플리케이션 환경 설정
    .env 파일 또는 환경 변수에서 자동으로 로드
    """
    
    # 애플리케이션 기본 설정
    APP_NAME: str = "Easy Welfare Guide"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True
    
    # Azure OpenAI 설정
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_API_DEPLOYMENT_NAME: str = "gpt-35-turbo"
    
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS 설정
    CORS_ORIGINS: list = ["*"]  # 프로덕션에서는 특정 도메인으로 제한
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: Optional[str] = None  # 로그 파일 경로 (None이면 콘솔만)
    
    # 테스트용 더미 데이터 경로
    DUMMY_DATA_PATH: Path = Path(__file__).resolve().parents[2] / 'test_dummy_data.json'

    # 프롬프트 설정
    PROMPTS_DIR: Path = Path(__file__).parent.parent / "agents" / "prompts"
    
    # 기타 설정
    MAX_CONTENT_LENGTH: int = 10000  # 최대 입력 텍스트 길이
    DEFAULT_REFINEMENT_LEVEL: int = 13  # 기본 난이도 (7 or 13)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 싱글톤 설정 인스턴스
settings = Settings()


# 설정 검증 함수
def validate_settings():
    """필수 설정 값 검증"""
    required_fields = [
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
    ]
    
    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field, None):
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(
            f"필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_fields)}\n"
            f".env 파일을 확인하세요."
        )


# 애플리케이션 시작 시 설정 검증
try:
    validate_settings()
except ValueError as e:
    print(f"⚠️  설정 오류: {e}")