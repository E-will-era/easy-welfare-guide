import sys
import os

current_path = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_path, "../../"))

if backend_root not in sys.path:
    sys.path.insert(0, backend_root) # 최우선 경로로 설정

from app.validater.human import get_human_guideline

class ValidateAgent:
    def __init__(self):
        self.guideline = get_human_guideline()
        if not self.guideline:
            raise ValueError("검증 가이드라인을 로드할 수 없습니다.")
        self.system_prompt = self._build_ai_optimized_prompt()

    def _build_ai_optimized_prompt(self):
        return f"""
<role>
{self.guideline['role']}
{self.guideline['objective_persona']}
</role>

<checkpoints>
1. 팩트 체크: {self.guideline['validation_checkpoints']['fact_accuracy']}
2. 완전성: {self.guideline['validation_checkpoints']['completeness']}
3. 중립성: {self.guideline['validation_checkpoints']['neutrality']}
4. 안전성: {self.guideline['validation_checkpoints']['safety']}
</checkpoints>

<rules>
- {self.guideline['rules_for_verification']['binary_judgment']['description']}
- {self.guideline['rules_for_verification']['evidence_required']['description']}
</rules>

<constraints>
{chr(10).join([f"- {c}" for c in self.guideline['constraints']])}
</constraints>

<output_format>
Return only the following JSON structure:
{self.guideline['output_format']['json_structure']}
</output_format>
""".strip()

    def run(self, source_text, target_text):
        """
        원문(source)과 생성물(target)을 비교 검증합니다.
        """
        print(f"--- [Validation Engine Running] ---")
        # 실제 호출 시: prompt + f"Source: {source_text}\nTarget: {target_text}"
        return "검증 프로세스 완료."

if __name__ == "__main__":
    agent = ValidateAgent()
    print(agent.system_prompt)