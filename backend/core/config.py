import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 운영적 안정성을 위해 최상위에서 로드
load_dotenv()

class Settings(BaseSettings):
    # Jira KAN-27 요구사항: AzureOpenAISettings 클래스 정의
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2023-05-15"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()