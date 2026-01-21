import os
import yaml

def get_human_guideline():
    """
    인간이 정의한 검증 가이드라인(validate_human.yaml)을 로드합니다.
    """
    current_path = os.path.dirname(os.path.abspath(__file__))
    # app/validater/ -> app/ -> backend/ (2단계 상위 이동)
    project_root = os.path.abspath(os.path.join(current_path, "../../")) 
    yaml_path = os.path.join(project_root, "prompts", "validate_human.yaml")
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: 검증 가이드라인 파일을 찾을 수 없습니다: {yaml_path}")
        return None