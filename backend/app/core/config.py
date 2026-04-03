import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List
from pydantic import field_validator


class Settings(BaseSettings):
    # 설명: 어플리케이션 내의 모든 구성값들을 담고 있습니다.
    # 작동 방식: pydantic_settings.BaseSettings를 상속하여 자동으로 환경
    #            변수 또는 .env 파일에서 설정값을 읽어옵니다. 별도의 값이 
    #            없을 시에는 필드에 지정된 기본값을 폴백(fallback)으로 적용합니다.
    # 반환값: 환경설정으로부터 자동 주입된 Settings 인스턴스.

    # Application base settings
    APP_NAME: str = "Easy Welfare Guide"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True

    # Generic LLM settings (OpenAI-compatible endpoint, e.g. vLLM serving EXAONE)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "http://localhost:8000/v1"   # Default vLLM endpoint
    LLM_MODEL_NAME: str = "LGAI-EXAONE/EXAONE-3.5-32B-Instruct"  # Default EXAONE model
    LLM_API_VERSION: Optional[str] = None  # Reserved for backward compatibility if needed

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS settings (supports string or list)
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        # 설명: 쉼표(,)로 구분된 문자열 혹은 리스트로부터 CORS 오리진을 파싱합니다.
        # 작동 방식: 값에 쉼표가 들어있는 문자열이라면 이를 분리하여 리스트로 만들고,
        #            일반 문자열이라면 요소가 하나인 리스트로 래핑하며, 이미 
        #            리스트 형식이라면 그 값을 그대로 리턴합니다.
        # 반환값: CORS 원본(origin) 문자열 배열(List).
        if isinstance(v, str):
            if "," in v:
                return [origin.strip() for origin in v.split(",")]
            return [v]
        return v

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    # Path to test dummy data
    DUMMY_DATA_PATH: Path = Path(__file__).resolve().parents[2] / 'test_dummy_data.json'

    # Prompt templates directory
    PROMPTS_DIR: Path = Path(__file__).parent.parent / "agents" / "prompts"

    # Miscellaneous settings
    MAX_CONTENT_LENGTH: int = 10000
    DEFAULT_REFINEMENT_LEVEL: int = 13

    # Upstage OCR settings
    UPSTAGE_API_KEY: str = ""

    # HuggingFace settings
    HF_TOKEN: str = ""
    HF_DATASET_REPO_ID: Optional[str] = None
    USE_HF_DATASET: bool = False
    HF_USE_RAW_FILES: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance
settings = Settings()

# HF_TOKEN을 OS 환경변수로 주입 — huggingface_hub가 모델 다운로드 시 자동 인증
if settings.HF_TOKEN:
    os.environ["HF_TOKEN"] = settings.HF_TOKEN


def validate_settings():
    # 설명: 런타임 환경에 필수적인 모든 환경 구성값들이 제공되었는지 검증합니다.
    # 작동 방식: 필수 필드 이름 목록을 반복돌면서 싱글톤(settings)에 데이터가 있는지
    #            확인하고, 누락되었거나 비어있을 경우 모아서 보고합니다.
    #            하나라도 누락되었을 경우 어떤 필드가 없는지 알려주며 ValueError를 발생시킵니다.
    # 반환값: 없음 (필수 필드가 모두 존재할 시 정상 통과).
    # 예외: 모든 누락 필수 필드 리스트를 나열한 ValueError 예외.
    required_fields = [
        "LLM_API_KEY",
        "LLM_BASE_URL",
    ]

    missing_fields = []
    for field in required_fields:
        value = getattr(settings, field, None)
        if not value or value == "":
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(
            f"Required environment variables are not set: {', '.join(missing_fields)}\n"
            f"Please check your .env file."
        )


# Validate settings on application startup
try:
    validate_settings()
except ValueError as e:
    print(f"Warning - Configuration error: {e}")
