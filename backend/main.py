from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import logger
from app.api.v1.endpoints.welfare_api import router as welfare_router
from app.api.v1.endpoints.test_api import router as test_router
from app.api.v1.endpoints.test_sse import router as test_sse_router

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
    welfare_router,  
    prefix="/api/v1",
    tags=["Welfare"]
)
app.include_router(
    test_router,
    prefix="/api/v1",
    tags=["Test"]
)
app.include_router(
    test_sse_router,
    prefix="/api/v1",
    tags=["Test SSE"]
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
    """서버 시작 시 실행"""
    logger.info("🔧 Easy Welfare Guide API 서버 시작")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("🛑 Easy Welfare Guide API 서버 종료")