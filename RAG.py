import os
from typing import List, Any, Dict
import openai
from dotenv import load_dotenv
from repo_processor import repo_processor

load_dotenv()

class RAG():
    def __init__(self, repo_url:str):
        self.repo_url   = repo_url
        self.repo_processor = repo_processor(self.repo_url)
        self.llm_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def setup_repo(self):
        self.repo_processor.clone_repo()
        self.repo_processor.process_repo()
    
    def search_relevant(self, query: str, n_results: int = 5) -> List[Dict[str,Any]]:
        return self.repo_processor.search_similar_to_query(query, n_results)
    def generate_context(self, search_results):
        """Generate context from search results"""
        context = ""
        for result in search_results:
            file_path = result['metadata']['file_path']  
            content = result['content']                   
            context += f"File: {file_path}\n```\n{content}\n```\n\n"
        return context
    
    def ask_question(self, question: str) -> str:
        search_results = self.search_relevant(query=question)
        if not search_results:
            return "No relevant content could be found, please try other questions"
        
        context = self.generate_context(search_results)

        prompt = f"""You are an expert code assistant. Based on the following code from a GitHub repository, answer the user's question.

        Repository Code Context:
        {context}

        User Question: {question}

        Please provide a detailed answer based on the code provided. Include code examples where relevant and explain how the code works."""

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"





    
      