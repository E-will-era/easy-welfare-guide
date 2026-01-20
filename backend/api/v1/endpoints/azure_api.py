from fastapi import APIRouter

router = APIRouter()

@router.post("/process")
async def process_azure_task():
    # KAN-10: 엔드포인트 틀 생성 완료
    # 추후 azure_client.py의 비동기 로직이 이곳에 연결될 예정입니다.
    return {"status": "success", "message": "Azure API Endpoint Ready"}