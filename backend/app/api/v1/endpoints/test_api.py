import json
from typing import List
from fastapi import APIRouter, HTTPException

from app.core.config import settings

router = APIRouter(prefix='/test', tags=['test'])

@router.get('/analyze', status_code=200)
async def get_test_dummy_data():
    '''
    returns:
        json_data:
    '''
    if not settings.DUMMY_DATA_PATH.exists():
        raise HTTPException(status_code=404, detail='테스트용 더미 데이터를 찾을 수 없습니다.')
    
    try:
        with open(file=settings.DUMMY_DATA_PATH, mode='r', encoding='utf-8') as file:
            data = json.load(file)
        
            return data
    
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=500, detail='유효하지 않은 JSON 형식입니다.')