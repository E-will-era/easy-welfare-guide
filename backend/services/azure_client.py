import os
import aiofiles
from openai import AsyncAzureOpenAI
from backend.core.config import settings # 중앙 설정 로드

class AzureOpenAIClient:
    def __init__(self):
        # os.getenv 대신 settings 객체를 사용하여 안정성 확보
        self.client = AsyncAzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )

    async def _get_prompt(self, filename: str):
        # backend_dir 경로 계산을 위해 os 모듈이 필요합니다.
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(backend_dir, "prompts", filename.strip())
        
        print(f"--- [DEBUG] Target Path: {prompt_path} ---")
        
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

        # 비동기 파일 읽기를 위해 aiofiles가 필요합니다.
        async with aiofiles.open(prompt_path, mode='r', encoding='utf-8') as f:
            return await f.read()

    async def get_summary(self, content: str):
        prompt_instruction = await self._get_prompt("summarize_ai.txt")
        
        response = await self.client.chat.completions.create(
            model="gpt-35-turbo",
            messages=[
                {"role": "system", "content": prompt_instruction},
                {"role": "user", "content": content}
            ]
        )
        return response.choices[0].message.content