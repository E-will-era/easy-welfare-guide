#!/bin/bash
# ============================================================
# Easy Welfare Guide - 빌드 스크립트
# ============================================================
# 사용법: ./scripts/build.sh [옵션]
# 옵션:
#   --frontend-only  : 프론트엔드만 빌드
#   --docker         : Docker 이미지 빌드
#   --push           : Docker 이미지를 HF에 푸시

set -e  # 에러 발생 시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Easy Welfare Guide - Build Script${NC}"
echo -e "${GREEN}========================================${NC}"

# 함수: 프론트엔드 빌드
build_frontend() {
    echo -e "\n${YELLOW}[1/3] Frontend 빌드 중...${NC}"
    cd "$PROJECT_ROOT/frontend"

    # node_modules 확인
    if [ ! -d "node_modules" ]; then
        echo "  npm install 실행 중..."
        npm install --legacy-peer-deps
    fi

    # 빌드
    echo "  npm run build 실행 중..."
    REACT_APP_API_URL="" npm run build

    echo -e "${GREEN}  ✅ Frontend 빌드 완료${NC}"
    cd "$PROJECT_ROOT"
}

# 함수: 빌드 파일을 백엔드로 복사
copy_static() {
    echo -e "\n${YELLOW}[2/3] 정적 파일 복사 중...${NC}"

    # 기존 static 폴더 삭제
    rm -rf "$PROJECT_ROOT/backend/static"

    # 빌드 결과물 복사
    cp -r "$PROJECT_ROOT/frontend/build" "$PROJECT_ROOT/backend/static"

    echo -e "${GREEN}  ✅ 정적 파일 복사 완료${NC}"
}

# 함수: Docker 이미지 빌드
build_docker() {
    echo -e "\n${YELLOW}[3/3] Docker 이미지 빌드 중...${NC}"
    cd "$PROJECT_ROOT"

    docker build -t easy-welfare-guide:latest .

    echo -e "${GREEN}  ✅ Docker 이미지 빌드 완료${NC}"
}

# 함수: 로컬 테스트 실행
run_local() {
    echo -e "\n${YELLOW}로컬 테스트 서버 실행 중...${NC}"
    cd "$PROJECT_ROOT/backend"

    # 가상환경 활성화 (있으면)
    if [ -d "venv" ]; then
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
    fi

    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

# 메인 로직
case "$1" in
    --frontend-only)
        build_frontend
        ;;
    --docker)
        build_docker
        ;;
    --local)
        build_frontend
        copy_static
        run_local
        ;;
    --help|-h)
        echo "사용법: ./scripts/build.sh [옵션]"
        echo ""
        echo "옵션:"
        echo "  (없음)           : 프론트엔드 빌드 + 정적 파일 복사"
        echo "  --frontend-only  : 프론트엔드만 빌드"
        echo "  --docker         : Docker 이미지 빌드"
        echo "  --local          : 빌드 후 로컬 서버 실행"
        echo "  --help, -h       : 도움말 표시"
        ;;
    *)
        build_frontend
        copy_static
        echo -e "\n${GREEN}========================================${NC}"
        echo -e "${GREEN}  빌드 완료!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo "다음 단계:"
        echo "  1. Docker 빌드: ./scripts/build.sh --docker"
        echo "  2. 로컬 테스트:  ./scripts/build.sh --local"
        echo "  3. HF 배포:     git push (HF Spaces 연결 후)"
        ;;
esac
