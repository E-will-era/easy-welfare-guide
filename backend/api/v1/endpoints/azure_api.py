from fastapi import APIRouter, HTTPException
from backend.schemas.summary import SummaryRequest, SummaryResponse
from openai import AzureOpenAI
import os
from dotenv import load_dotenv  # 추가!

load_dotenv()

router = APIRouter()

# 환경변수 출력해서 확인 (디버깅용)
print("=== 환경변수 확인 ===")
print(f"API_KEY: {os.getenv('AZURE_OPENAI_API_KEY')}")
print(f"ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
print(f"VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
print(f"DEPLOYMENT: {os.getenv('AZURE_OPENAI_API_DEPLOYMENT_NAME')}")

# Azure OpenAI 클라이언트 설정
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

@router.post("/process", response_model=SummaryResponse)
async def process_azure_task(request: SummaryRequest):
    try:
        # Azure OpenAI API 호출 (올바른 방법)
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_API_DEPLOYMENT_NAME"),
            messages=[
                {"role": "system", "content": "복지 정보를 쉽게 요약해주는 AI입니다."},
                {"role": "user", "content": f"다음 내용을 요약해주세요: {request.content}"}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        summary_result = response.choices[0].message.content
        
        return {"summary": summary_result, "status": "success"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))