# 복지 안내문 쉬운말 도우미 서비스
마이크로소프트 ai 엔지니어 과정 3기 미니 프로젝트:  복지 안내문 쉬운말 도우미 서비스.

## 🚀 빠른 시작

### 📚 Local

#### 1. 저장소 클론

```bash
git clone https://github.com/E-will-era/easy-welfare-guide.git
cd easy-welfare-guide
```

#### 2. 가상환경 설정

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r bakend/requirements.txt
```

#### 3. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 설정 입력
```

#### 4. 서버 실행

```bash
# FastAPI 서버
uvicorn bakend:app --reload --port 8000

```

#### 5. 클라이언트 실행
```bash
cd frontend
npm install
npm start
```

### 📚 통합 실행

`run.sh` 스크립트를 사용하여 프론트엔드와 백엔드를 동시에 실행할 수 있습니다.

**Bash (Git Bash 등) 환경:**
```bash
./run.sh
```
실행 시, 백엔드는 포트 8000번, 프론트엔드는 기본 포트(보통 3000번)에서 실행됩니다.
스크립트 종료 시(Ctrl+C), 두 서버 모두 종료됩니다.
