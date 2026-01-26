# Back-End

## FastAPI 시작 가이드

### Local

#### 1. backend 폴더로 이동
```bash
cd .\backend\
```

#### 2. 가상 환경 생성 및 활성화
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

#### 3. 필수 의존성 설치
```bash
pip install -r requirements.txt
```

#### 4. 환경 변수 설정
```bash
cp backend/env_template .env
```

#### 5. 웹 서버 실행
```bash
uvicorn main:app --reload --port 8000
```