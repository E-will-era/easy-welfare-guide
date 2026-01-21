import logging
from logging.handlers import RotatingFileHandler
# 상대 경로(from .config) 대신 절대 경로 사용
from backend.core.config import settings 

def setup_logger(name: str = "app_logger"):
    logger = logging.getLogger(name)
    
    # 설정값 반영
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] - %(message)s"
        )

        # 1. 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. 파일 핸들러 (Rotating 설정)
        file_handler = RotatingFileHandler(
            settings.LOG_FILE_PATH, 
            maxBytes=10*1024*1024, # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# 전역 로거 인스턴스
logger = setup_logger()

if __name__ == "__main__":
    logger.info("로거가 성공적으로 초기화되었습니다.")