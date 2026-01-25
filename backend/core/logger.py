import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from core.config import settings

def setup_logger(name: str = "easy-welfare-guide") -> logging.Logger:
    """
    애플리케이션 로거 설정
    
    Args:
        name: 로거 이름
        
    Returns:
        설정된 Logger 인스턴스
    """
    logger = logging.getLogger(name)
    
    # 로그 레벨 설정
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 이미 핸들러가 있으면 중복 추가 방지
    if logger.handlers:
        return logger
    
    # 포맷터 설정
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 1. 콘솔 핸들러 (항상 추가)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    # 2. 파일 핸들러 (선택적)
    if settings.LOG_FILE:
        try:
            # 로그 디렉토리 생성
            log_file = Path(settings.LOG_FILE)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 파일 핸들러 추가
            file_handler = RotatingFileHandler(
                filename=str(log_file),
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)
            
            logger.info(f"File logging enabled: {log_file}")
            
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {e}")
    
    # 상위 로거로 전파 방지 (중복 로그 방지)
    logger.propagate = False
    
    return logger


# 전역 로거 인스턴스
logger = setup_logger()


# 로거 헬퍼 함수들
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    지정된 이름의 로거 반환
    
    Args:
        name: 로거 이름 (None이면 기본 로거)
        
    Returns:
        Logger 인스턴스
    """
    if name:
        return logging.getLogger(f"easy-welfare-guide.{name}")
    return logger


def set_log_level(level: str):
    """
    로그 레벨 동적 변경
    
    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    for handler in logger.handlers:
        handler.setLevel(log_level)
    logger.info(f"Log level changed to: {level.upper()}")


# 테스트 코드
if __name__ == "__main__":
    logger.debug("This is a debug message")
    logger.info("로거가 성공적으로 초기화되었습니다.")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # 모듈별 로거 테스트
    agent_logger = get_logger("agents")
    agent_logger.info("Agent logger test")
    
    api_logger = get_logger("api")
    api_logger.info("API logger test")