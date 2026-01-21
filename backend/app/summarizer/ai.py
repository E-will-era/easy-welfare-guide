import sys
import os

# 1. 현재 파일의 위치를 기준으로 backend 폴더를 찾아 sys.path에 추가
current_path = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_path, "../../"))

if backend_root not in sys.path:
    sys.path.insert(0, backend_root) # 최우선 경로로 설정

from app.summarizer.human import get_human_guideline

class SummarizeAgent:
    def __init__(self):
        # 1. 원칙(Ground Truth) 로드
        self.guideline = get_human_guideline()
        if not self.guideline:
            raise ValueError("요약 가이드라인을 로드할 수 없습니다.")
            
        # 2. AI 실행용 최적화 프롬프트 구축
        self.system_prompt = self._build_ai_optimized_prompt()

    def _build_ai_optimized_prompt(self):
        # YAML의 세분화된 규칙을 LLM 실행 명령어로 변환
        return f"""
<role>
{self.guideline['role']}
{self.guideline['objective_persona']}
</role>

<extraction_targets>
추출 우선순위:
- 대상: {self.guideline['extraction_targets']['target_audience']}
- 혜택: {self.guideline['extraction_targets']['benefits']}
- 조건: {self.guideline['extraction_targets']['conditions']}
- 방법: {self.guideline['extraction_targets']['how_to_apply']}
</extraction_targets>

<execution_rules>
1. {self.guideline['rules_for_precision']['quantitative_focus']['description']}
   예시: {self.guideline['rules_for_precision']['quantitative_focus']['example']}
2. {self.guideline['rules_for_precision']['structural_summary']['description']}
3. {self.guideline['rules_for_precision']['no_inference']['description']}
</execution_rules>

<constraints>
{chr(10).join([f"- {c}" for c in self.guideline['constraints']])}
</constraints>

<output_format>
반드시 아래 JSON 구조로만 응답하십시오:
{self.guideline['output_format']['json_structure']}
</output_format>
""".strip()

    def run(self, raw_text):
        """
        실제 요약 실행 함수 (예시)
        """
        print(f"--- [Summarizer Engine Running] ---")
        # 실제 환경에서는 여기서 azure_client 등을 호출합니다.
        # response = self.client.generate(system=self.system_prompt, user=raw_text)
        return "정보 추출 및 정량적 요약 완료."

if __name__ == "__main__":
    agent = SummarizeAgent()
    print("--- [AI Optimized Prompt for Summarizer] ---")
    print(agent.system_prompt)