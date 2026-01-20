from fastapi import FastAPI
from backend.api.v1.endpoints import azure_api  # 새로 만든 라우터 임포트

app = FastAPI()

# 라우터 연결: /api/v1/azure/process 경로로 접근 가능하게 설정
app.include_router(azure_api.router, prefix="/api/v1/azure", tags=["Azure"])

@app.get("/")
def read_root():
    return {"Hello": "World"}