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
        # 1. 절대 경로 직접 지정 (가장 확실한 방법)
        # 띄어쓰기 오타가 발생하지 않도록 filename을 그대로 조인합니다.
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(backend_dir, "prompts", filename.strip())
        
        # [검증] 터미널에 찍히는 이 경로를 복사해서 확인해 보세요.
        print(f"--- [DEBUG] Target Path: {prompt_path} ---")
        
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")

        async with aiofiles.open(prompt_path, mode='r', encoding='utf-8') as f:
            return await f.read()

    async def get_summary(self, content: str):
        # 여기서 파일명에 공백이 들어가지 않도록 주의하세요!
        prompt_instruction = await self._get_prompt("summarize_ai.txt")
        
        response = await self.client.chat.completions.create(
            model="gpt-35-turbo",
            messages=[
                {"role": "system", "content": prompt_instruction},
                {"role": "user", "content": content}
            ]
        )
        return response.choices[0].message.content