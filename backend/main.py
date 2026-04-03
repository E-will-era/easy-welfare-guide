from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.logger import logger
from app.api.v1.endpoints.welfare_api import router as welfare_router
from app.api.v1.endpoints.test_api import router as test_router
from app.api.v1.endpoints.chat_api import router as chat_router

# 정적 파일 경로 (Docker 빌드 시 React 빌드 결과물 위치)
STATIC_DIR = Path(__file__).parent / "static"

# FastAPI 앱 초기화
app = FastAPI(
    title="Easy Welfare Guide API",
    description="복지 정보 안내 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
    chat_router,
    prefix="/api/v1",
    tags=["Eligibility & Documents"]
)

# ------------------------------------------------------------
# 정적 파일 서빙 (React SPA)
# ------------------------------------------------------------
if STATIC_DIR.exists():
    # Static files (JS, CSS, images, etc.)
    app.mount("/static", StaticFiles(directory=STATIC_DIR / "static"), name="static")

    @app.get("/")
    async def serve_react_app():
        """
        설명: 리액트 배포 환경(루트 URL)의 SPA 엔트리 포인트(Entry Point) 진입점.
        작동 방식: 이미 브라우저 구동용으로 완전하게 빌드 되어있는 static 디렉토리 내의 
            index.html 데이터를 브라우저 부트스트랩 어플리케이션 용도로써 곧바로 파일 전송을 응답.
        반환값: FileResponse 인스턴스가 래핑하고 있는 STATIC_DIR/index.html 데이터 반환.
        예외: 특별한 자체 발생 예외가 없으며 만약 누락된 파일 이슈가 도달할 경우 FastAPI단이 처리함.
        """
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_react_routes(full_path: str):
        """
        설명: 클라이언트 단에서 구동되는 모든 서브루팅 React Router 내비게이션 처리를 보완해주는 포괄(Catch-all) 라우터.
        작동 방식: "api/" 라고 선행되는 특수 경로명들을 벗어난 그 외의 임의의 요청 루트들을 
            리액트 어플리케이션이 파악하는 React Router 형식으로 제공해주게 되며 실제 파일명이 있다면 직접반환, 그게 아니면 index.html 반환.
        반환값: 내부적으로 일치하는 static file 또는 fallback으로서의 최상위 index.html 응답반환(FileResponse 형태).
        예외: 반환값 자체가 404가 나오는 경우가 발생하지 않는 대신에, 만약 api형식 이면서 어떠한 내부 등록 포인터와도 연결 안될경우, "detail": "Not Found" JSON 만을 표출합니다.
        """
        # API 서브패스와 경로 일치 실패 시 404형 에러 반환
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}

        # Serve the file directly if it exists in the static directory
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # 기타 모든 그 외 경로들은 프론트인 React Router 가 캐치하여 띄워주게끔 root index 파일 처리
        return FileResponse(STATIC_DIR / "index.html")
else:
    # 정적 파일 없음 — 로컬 개발 모드 지원 모듈 작동
    @app.get("/")
    def read_root():
        """
        설명: 로컬 개발 시 앱이 잘 돌고 있는지를 감지하기 위해 준비된 기초환영 페이지 및 헬스 체크포인트 구역입니다.
        작동 방식: React 의 build결과 아울렛들을 현재 보유하고 서빙 중이지 못하는 로컬 세션에서는 
             현재의 status 관련 응답 정보만을 리플라이 해줍니다 (리액트는 단독 프지포트 3000포트를 가지기 때문).
        반환값: status, message, mode, note 등을 포함하고 있는 Dict 맵퍼.
        예외: 없음.
        """
        return {
            "status": "ok",
            "message": "Easy Welfare Guide API is running",
            "mode": "development",
            "note": "React frontend is served separately on port 3000"
        }


@app.get("/health")
def health_check():
    """
    설명: 로드밸런싱이나 컨테이너 모니터링 프로빙 툴들에 활용하기 좋도록 구성된 좀더 심도깊은 앱 진단 및 헬스 체크 엔드포인트입니다.
    작동 방식: 버전(Version) 이라던지 내부 런타임 Environment 정보 변환 값을 직접 대조시켜줌으로써 모니터링 시스템 인프라 구축의 이점을 줘 앱 작동 유무의 판단 정확성을 향상 시킵니다.
    반환값: status, version, environment.
    예외: 없음.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.on_event("startup")
async def startup_event():
    """
    설명: 웹 어플리케이션이 기동 되었을 때 필수적으로 사전 실행되어야 하는 초기 런타임 루팅 절차 이벤트를 수행합니다.
    작동 방식: 
        1. 옵저버 빌리티를 위한 현재 구동 중인 환경 및 로컬 개발용 Static File 서빙 준비도 기록.
        2. 공통 싱글톤 세션매니저를 인스턴스화 하고 start_cleanup() 펑션을 불러들임으로써 만료된 스레기값 세션들을 
           비동기 백그라운드 환경 상에서 청소하는 역할을 부여함 (FastAPI 라이프사이클 이벤트 위에서 시작하도록 함)
    반환값: 없음.
    예외: 구동 루프가 올바르지 않으면 발생할 수있는 RuntimeError (기본적인 FastAPI/Uvicorn 설정에서는 발견되지 않는 이슈).
    """
    logger.info("Easy Welfare Guide API server starting")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    if STATIC_DIR.exists():
        logger.info(f"Serving static files from: {STATIC_DIR}")
    else:
        logger.info("No static files found (development mode)")

    from app.core.session_manager import get_session_manager
    get_session_manager().start_cleanup()
    logger.info("Session manager cleanup task started")


@app.on_event("shutdown")
async def shutdown_event():
    """
    설명: 서빙 프로그램이 종료 및 정지될때 실행되어 서버 내부를 청결하게 끄는 클린업 타임 이벤트를 담당.
    작동 방식: 셧다운 이벤트 로깅. 공용 Session Manager 안에 남겨진 이벤트 루프가 스스로 소멸 및 취소처리.
    반환값: 없음.
    예외: 없음.
    """
    logger.info("Easy Welfare Guide API server shutting down")
