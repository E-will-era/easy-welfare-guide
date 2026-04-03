---
title: Easy Welfare Guide
emoji: 📋
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Easy Welfare Guide (복지 안내문 쉬운말 도우미)

어려운 복지 안내문을 초등학생도 이해할 수 있는 쉬운 말로 바꿔주는 AI 서비스입니다.

## 주요 기능

- 📸 **이미지 업로드**: 복지 안내문 사진을 업로드
- 🔍 **OCR 텍스트 추출**: Azure OpenAI Vision으로 텍스트 추출
- 📚 **RAG 검색**: 복지 정책 데이터베이스에서 관련 정보 검색
- ✨ **쉬운말 변환**: 전문 용어를 초등학생 수준으로 순화

## 기술 스택

- **Frontend**: React 19, Material-UI
- **Backend**: FastAPI, Python 3.11
- **AI**: Azure OpenAI GPT-4
- **Vector DB**: ChromaDB + BM25 하이브리드 검색
- **Embedding**: BAAI/bge-base-en-v1.5
- **Reranking**: BAAI/bge-reranker-v2-m3

## 라이선스

MIT License
