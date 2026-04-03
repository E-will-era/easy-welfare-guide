# ============================================================
# Easy Welfare Guide - HuggingFace Spaces Dockerfile
# Multi-stage build: React frontend + FastAPI backend
# ============================================================

# ------------------------------------------------------------
# Stage 1: Build React Frontend
# ------------------------------------------------------------
FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend

# 패키지 파일 복사 및 의존성 설치
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

# 소스 복사 및 빌드
COPY frontend/ ./

# 환경변수 설정 (빌드 시 API URL은 상대 경로 사용)
ENV REACT_APP_API_URL=""

RUN npm run build

# ------------------------------------------------------------
# Stage 2: Python Backend + Static Files
# ------------------------------------------------------------
FROM python:3.11-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치 (캐시 활용을 위해 먼저 복사)
COPY backend/requirements.txt ./requirements.txt

# HuggingFace Hub 의존성 추가
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir huggingface_hub datasets

# 백엔드 소스 복사
COPY backend/ ./

# React 빌드 결과물 복사 (정적 파일)
COPY --from=frontend-builder /app/frontend/build ./static

# 로그 디렉토리 생성
RUN mkdir -p logs

# HuggingFace 캐시 디렉토리 설정
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
RUN mkdir -p /app/.cache/huggingface

# 환경변수 기본값 (HF Spaces에서 덮어씀)
ENV ENVIRONMENT=production
ENV DEBUG=False
ENV LOG_LEVEL=INFO
ENV HOST=0.0.0.0
ENV PORT=7860

# HuggingFace Spaces 설정
ENV USE_HF_DATASET=True
ENV HF_USE_RAW_FILES=True

# HuggingFace Spaces는 7860 포트 사용
EXPOSE 7860

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# 서버 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
