import json
import asyncio
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix='/test')

# 테스트용 task 저장소
test_tasks = {}

# 2차 질의용 요청 스키마
class RetryAnalyzeRequest(BaseModel):
    admin_summary: str

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
                "plain_summary": "### [테스트] 연습용 안내입니다 🧪\n\n안녕하세요! 이 글은 **화면 테스트**를 위해 작성된 가짜 내용입니다.\n\n1. **실제 사업이 아니에요**\n   실제로 지원금을 주거나 신청을 받는 내용이 아닙니다.\n2. **확인해주세요**\n   글자 모양(굵게, 제목 등)이 잘 보이는지 확인하기 위함입니다.\n\n> 개발팀에서 시스템 점검 중입니다.",
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


# ============================================
# 2차 질의용 API (답변 재생성)
# ============================================

@router.post('/analyze/retry/start', status_code=200)
async def start_retry_analyze(request: RetryAnalyzeRequest):
    '''
    2차 질의용 분석 시작 엔드포인트
    admin_summary를 받아서 답변 재생성만 수행
    '''
    if not request.admin_summary:
        raise HTTPException(status_code=400, detail='admin_summary가 필요합니다.')

    task_id = str(uuid.uuid4())
    test_tasks[task_id] = {"type": "retry", "admin_summary": request.admin_summary}

    return {
        "status": "pending",
        "data": {
            "task_id": task_id,
            "sse_stream_uri": f"/api/v1/test/analyze/retry/{task_id}/stream"
        }
    }


@router.get('/analyze/retry/{task_id}/stream')
async def retry_analyze_stream(task_id: str):
    '''
    2차 질의용 SSE 스트림 엔드포인트
    답변 재생성만 수행하므로 regenerate → validate → completed 순서로 진행
    '''
    if task_id not in test_tasks:
        raise HTTPException(status_code=404, detail='해당 task_id를 찾을 수 없습니다.')

    task_info = test_tasks[task_id]
    if task_info.get("type") != "retry":
        raise HTTPException(status_code=400, detail='잘못된 task 타입입니다.')

    async def event_generator():
        phases = [
            ("regenerate", "답변 재생성 중..."),
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

        # 최종 완료 응답 (2차 질의용 더미 데이터 - 더 상세한 내용)
        completed_data = {
            "status": "completed",
            "data": {
                "task_id": task_id,
                "plain_summary": "【누가 받을 수 있나요? (자세히)】\n• 기초생활수급자: 소득이 적어 기본 생활이 어려운 분\n  → 4인 가구 기준 월 소득 약 162만원 이하\n• 차상위계층: 기초수급자보다는 조금 나은 형편이지만 도움이 필요한 분\n  → 4인 가구 기준 월 소득 약 270만원 이하\n• 65세 이상 어르신\n• 장애가 있으신 분 (장애 정도 상관없이)\n\n【무엇을 받을 수 있나요? (자세히)】\n• 생활비 지원\n  → 혼자 사시면 월 10만원\n  → 4인 가족이면 월 30만원까지\n• 병원비 할인: 내야 할 금액의 절반까지 깎아줘요\n• 집 수리 도움: 도배, 장판, 보일러 고장 등 최대 500만원까지\n\n【어떻게 신청하나요?】\n• 가까운 주민센터에 가세요\n• 인터넷으로도 가능해요 (복지로 사이트)\n• 가져갈 것: 신분증, 소득 서류, 가족관계증명서",
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