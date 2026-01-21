import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Azure OpenAI Settings
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2023-05-15"

    # --- 로깅 설정 추가 ---
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_FILE_NAME: str = "app.log"

    @property
    def LOG_FILE_PATH(self) -> str:
        # 로그 디렉토리가 없으면 생성
        if not os.path.exists(self.LOG_DIR):
            os.makedirs(self.LOG_DIR)
        return os.path.join(self.LOG_DIR, self.LOG_FILE_NAME)
    # ---------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()