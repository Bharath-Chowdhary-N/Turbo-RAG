import os
from typing import List, Any, Dict
import openai
from dotenv import load_dotenv
from repo_processor import repo_processor

load_dotenv()

class RAG():
    def __init__(self, repo_url:str):
        self.repo_url   = repo_url
        self.llm_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        

    
      