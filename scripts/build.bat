@echo off
REM ============================================================
REM Easy Welfare Guide - Windows 빌드 스크립트
REM ============================================================
REM 사용법: scripts\build.bat [옵션]
REM 옵션:
REM   frontend  : 프론트엔드만 빌드
REM   docker    : Docker 이미지 빌드
REM   local     : 빌드 후 로컬 서버 실행

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo ========================================
echo   Easy Welfare Guide - Build Script
echo ========================================

if "%1"=="frontend" goto :frontend
if "%1"=="docker" goto :docker
if "%1"=="local" goto :local
if "%1"=="help" goto :help
if "%1"=="-h" goto :help

REM 기본: 프론트엔드 빌드 + 정적 파일 복사
call :frontend
call :copy_static
goto :done

:frontend
echo.
echo [1/3] Frontend 빌드 중...
cd frontend

if not exist "node_modules" (
    echo   npm install 실행 중...
    npm install --legacy-peer-deps
)

echo   npm run build 실행 중...
set "REACT_APP_API_URL="
npm run build

echo   Frontend 빌드 완료!
cd ..
goto :eof

:copy_static
echo.
echo [2/3] 정적 파일 복사 중...

if exist "backend\static" rmdir /s /q "backend\static"
xcopy /e /i /q "frontend\build" "backend\static"

echo   정적 파일 복사 완료!
goto :eof

:docker
echo.
echo [3/3] Docker 이미지 빌드 중...
docker build -t easy-welfare-guide:latest .
echo   Docker 이미지 빌드 완료!
goto :done

:local
call :frontend
call :copy_static
echo.
echo 로컬 테스트 서버 실행 중...
cd backend
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
goto :done

:help
echo.
echo 사용법: scripts\build.bat [옵션]
echo.
echo 옵션:
echo   (없음)    : 프론트엔드 빌드 + 정적 파일 복사
echo   frontend  : 프론트엔드만 빌드
echo   docker    : Docker 이미지 빌드
echo   local     : 빌드 후 로컬 서버 실행
echo   help, -h  : 도움말 표시
goto :done

:done
echo.
echo ========================================
echo   완료!
echo ========================================
echo.
echo 다음 단계:
echo   1. Docker 빌드: scripts\build.bat docker
echo   2. 로컬 테스트:  scripts\build.bat local
echo   3. HF 배포:     git push (HF Spaces 연결 후)
