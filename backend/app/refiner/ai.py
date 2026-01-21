from app.refiner.human import get_human_guideline

class RefineAgent:
    def __init__(self):
        # 1. 인간의 가이드라인 로드 (Ground Truth)
        self.guideline = get_human_guideline("refine_human.yaml")
        if not self.guideline:
            raise ValueError("가이드라인을 불러오지 못했습니다.")
            
        # 2. AI 최적화 프롬프트 생성
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self):
        # XML 태그를 활용한 구조화 (AI 성능 최적화)
        return f"""
<role>
{self.guideline['role']}
{self.guideline['objective_persona']}
</role>

<rules_by_level>
- Level 13 (초등 6학년): {self.guideline['rules_by_level']['level_13']['description']}
- Level 7 (유치원): {self.guideline['rules_by_level']['level_7']['description']}
</rules_by_level>

<constraints>
{chr(10).join([f"- {c}" for c in self.guideline['constraints']])}
</constraints>

<output_format>
반드시 아래 JSON 구조로만 응답하십시오:
{self.guideline['output_format']['json_structure']}
</output_format>
""".strip()

    def run(self, input_text, level=13):
        # 실행 로직 예시
        print(f"[{level} 수준 순화 시작]")
        # 실제 API 호출 시 self.system_prompt 사용
        return f"순화 프로세스 작동 중... (입력: {input_text[:10]}...)"

if __name__ == "__main__":
    agent = RefineAgent()
    print("--- 생성된 AI 최적화 프롬프트 ---")
    print(agent.system_prompt)