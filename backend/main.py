import sys
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from backend.api.v1.endpoints import azure_api  # 경로 최적화
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# 에이전트 모듈 로드를 위한 시스템 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.app.summarizer.ai import SummarizeAgent
from backend.app.refiner.ai import RefineAgent
from backend.app.validater.ai import ValidateAgent

# --- [비즈니스 로직 에이전트 클래스] ---
class EasyWelfareApp:
    def __init__(self):
        # 1. 에이전트 초기화 (각 폴더의 ai.py 클래스 호출)
        self.summarizer = SummarizeAgent()
        self.refiner = RefineAgent()
        self.validater = ValidateAgent()

    def process_welfare_info(self, raw_text, target_level=13):
        """
        전체 파이프라인 실행: 요약 -> 순화 -> 검증
        """
        print(f"\n[Step 1] 정보 요약 시작...")
        summary_result = self.summarizer.run(raw_text)
        
        # TODO: 실제 API 연동 시 summary_result에서 텍스트 추출 필요
        extracted_text = summary_result 

        print(f"[Step 2] 언어 순화 시작 (Level: {target_level})...")
        refined_text = self.refiner.run(extracted_text, level=target_level)

        print(f"[Step 3] 최종 품질 검증 시작...")
        validation_report = self.validater.run(raw_text, refined_text)

        return {
            "original": raw_text,
            "summarized": extracted_text,
            "refined": refined_text,
            "validation": validation_report
        }

# --- [FastAPI 서버 설정] ---
api_app = FastAPI()
app = api_app 

# CORS 설정 추가 (라우터 등록 전에!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경용 (모든 도메인 허용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 연결
api_app.include_router(azure_api.router, prefix="/api/v1/azure", tags=["Azure"])

@api_app.get("/")
def read_root():
    return {"status": "Easy Welfare Guide API is running"}

# --- [로컬 실행 테스트] ---
if __name__ == "__main__":
    # 1. 에이전트 파이프라인 테스트
    processor = EasyWelfareApp()
    test_text = "이 사업은 중위소득 150% 이하 가구를 대상으로 월 30만원의 바우처를 제공합니다."
    result = processor.process_welfare_info(test_text, target_level=7)
    
    print("\n" + "="*50)
    print("최종 파이프라인 실행 결과 확인")
    print(result)
    print("="*50)