import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

class AzureOpenAIClient:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2023-05-15",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )