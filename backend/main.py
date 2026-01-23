from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.logger import logger
from backend.api.v1.endpoints.welfare_api import router as welfare_router

# FastAPI 앱 초기화
app = FastAPI(
    title="Easy Welfare Guide API",
    description="복지 정보 안내 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(
    welfare_router,  # 이렇게!
    prefix="/api/v1",
    tags=["Welfare"]
)

@app.get("/")
def read_root():
    """헬스체크 엔드포인트"""
    return {
        "status": "ok",
        "message": "Easy Welfare Guide API is running"
    }

@app.get("/health")
def health_check():
    """상세 헬스체크"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Easy Welfare Guide API 서버 시작")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Easy Welfare Guide API 서버 종료")