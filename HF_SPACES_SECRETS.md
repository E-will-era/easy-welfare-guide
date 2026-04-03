# HuggingFace Spaces Secrets 설정 가이드

HF Spaces에서 Settings > Repository secrets에 다음 환경변수를 설정하세요.

## 필수 환경변수

| 변수명 | 값 | 설명 |
|--------|-----|------|
| `AZURE_OPENAI_API_KEY` | `your-api-key` | Azure OpenAI API 키 |
| `AZURE_OPENAI_ENDPOINT` | `https://xxx.openai.azure.com/` | Azure OpenAI 엔드포인트 |

## 선택 환경변수 (기본값 있음)

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `AZURE_OPENAI_API_VERSION` | `2024-12-01-preview` | API 버전 |
| `AZURE_OPENAI_API_DEPLOYMENT_NAME` | `gpt-4.1-2` | 배포된 모델명 |
| `ENVIRONMENT` | `production` | 환경 (Dockerfile에서 설정) |
| `DEBUG` | `False` | 디버그 모드 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `CORS_ORIGINS` | `*` | CORS 허용 도메인 |
| `USE_HF_DATASET` | `True` | HF에서 벡터 DB 다운로드 (Dockerfile에서 설정) |
| `HF_DATASET_REPO_ID` | `E-will-era/welfare-rag-vectors` | 벡터 DB 레포지토리 |
| `HF_USE_RAW_FILES` | `True` | ChromaDB 파일 직접 다운로드 |

## 설정 방법

1. HuggingFace Spaces 페이지에서 **Settings** 탭 클릭
2. **Repository secrets** 섹션으로 스크롤
3. **New secret** 버튼 클릭
4. 변수명과 값 입력 후 저장
5. Space 재시작 (Settings > Factory reboot)

## 주의사항

- API 키는 절대 코드에 직접 입력하지 마세요
- Secrets에 저장된 값은 로그에 노출되지 않습니다
- CORS_ORIGINS를 여러 개 설정할 때는 쉼표로 구분:
  ```
  https://your-app.hf.space,https://your-domain.com
  ```
