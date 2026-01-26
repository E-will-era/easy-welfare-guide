import json
import asyncio
import uuid
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings

router = APIRouter(prefix='/test')

# 테스트용 task 저장소
test_tasks = {}

@router.post('/analyze/start', status_code=200)
async def start_test_analyze():
    '''
    SSE 테스트용 분석 시작 엔드포인트
    실제 /api/analyze와 동일한 응답 형식
    '''
    task_id = str(uuid.uuid4())
    test_tasks[task_id] = True

    return {
        "status": "pending",
        "data": {
            "task_id": task_id,
            "sse_stream_uri": f"/api/v1/test/analyze/{task_id}/stream"
        }
    }


@router.get('/analyze/{task_id}/stream')
async def test_analyze_stream(task_id: str):
    '''
    SSE 테스트용 스트림 엔드포인트
    search → summarize → translate → validate → completed 순서로 진행
    '''
    if task_id not in test_tasks:
        raise HTTPException(status_code=404, detail='해당 task_id를 찾을 수 없습니다.')

    async def event_generator():
        phases = [
            ("search", "RAG 검색 중..."),
            ("summarize", "문서 요약 중..."),
            ("translate", "순화어 변환 중..."),
            ("validate", "검증 중...")
        ]

        # 각 phase를 2초 간격으로 전송
        for phase, _ in phases:
            data = {
                "status": "processing",
                "data": {
                    "phase": phase
                }
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(2)

        # 최종 완료 응답
        completed_data = {
            "status": "completed",
            "data": {
                "task_id": task_id,
                "admin_summary": "【지원 대상】\n• 기초생활수급자 및 차상위계층\n• 만 65세 이상 노인\n• 장애인복지법에 따른 등록 장애인\n\n【지원 내용】\n• 월 최대 30만원 생활지원금\n• 의료비 본인부담금 감면\n• 주거환경 개선 지원",
                "plain_summary": "【누가 받을 수 있나요?】\n• 생활이 어려운 분들 (기초생활수급자, 차상위계층)\n• 65세 이상 어르신\n• 장애가 있으신 분\n\n【무엇을 받을 수 있나요?】\n• 한 달에 최대 30만원 생활비 지원\n• 병원비 할인\n• 집 수리 도움",
                "references": [
                    {
                        "title": "2024년 기초생활보장 사업안내",
                        "resource": "https://www.mohw.go.kr"
                    },
                    {
                        "title": "노인복지 서비스 안내",
                        "resource": "https://www.bokjiro.go.kr"
                    }
                ]
            }
        }
        yield f"data: {json.dumps(completed_data, ensure_ascii=False)}\n\n"

        # task 정리
        del test_tasks[task_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )