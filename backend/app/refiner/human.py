import os
import yaml

def get_human_guideline(prompt_filename):
    """
    인간이 정의한 가이드라인(YAML)을 로드합니다.
    경로: backend/prompts/refine_human.yaml
    """
    # 현재 파일(human.py)의 위치: backend/app/refiner/
    current_path = os.path.dirname(os.path.abspath(__file__))
    
    # 두 단계 위로 이동: backend/
    project_backend_root = os.path.abspath(os.path.join(current_path, "../../")) 
    
    # 최종 경로: backend/prompts/refine_human.yaml
    yaml_path = os.path.join(project_backend_root, "prompts", prompt_filename)
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: 파일을 찾을 수 없습니다. 예상 경로 -> {yaml_path}")
        return None

if __name__ == "__main__":
    # 테스트 실행
    data = get_human_guideline("refine_human.yaml")
    if data:
        print(f"성공적으로 로드됨: {data['agent_name']}")