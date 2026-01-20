import os
import aiofiles  # 비동기 파일 처리를 위해 필요
from openai import AsyncAzureOpenAI # 비동기 클라이언트 사용 필수
from dotenv import load_dotenv

load_dotenv()

class AzureOpenAIClient:
    def __init__(self):
        # 반드시 'Async'AzureOpenAI를 사용해야 비동기 로직이 작동합니다.
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

    # [2단계 로직] 클래스 내부에 배치
    async def _get_prompt(self, filename: str):
        # 현재 위치가 backend/services/ 이므로 
        # prompts 폴더는 상위로 두 번 올라가야 할 수도 있습니다 (구조에 따라 확인 필요)
        # 안전한 경로 설정을 위해 os.path를 권장합니다.
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        prompt_path = os.path.join(base_path, "prompts", filename)
        
        async with aiofiles.open(prompt_path, mode='r', encoding='utf-8') as f:
            return await f.read()

    # [3단계 로직] 위에서 만든 _get_prompt를 활용
    async def get_summary(self, content: str):
        prompt_instruction = await get_prompt("summarize_ai.txt")
        response = await self.client.chat.completions.create(
        model="gpt-35-turbo", # 팀의 모델명으로 수정
        messages=[
            {"role": "system", "content": prompt_instruction},
            {"role": "user", "content": content}
        ]
    )
        return response.choices[0].message.content