# import ollama
# import asyncio
# from core.settings import settings
# from core.embedding import get_embedding_model
# from database.pgvektor import get_pgvector_connection
# from core.rag import RAGPipeline

# try:
#     conn = get_pgvector_connection()
#     rag = RAGPipeline(db_connection=conn)
# except Exception as e:
#     print(f"Warning: RAG initialization failed: {e}")
#     conn = None
#     rag = None

# def get_llm():
#     return ollama.Client(
#         host=settings.OLLAMA_HOST
#     )

# def generate_text(prompt: str):
#     client = get_llm()
#     return client.generate(
#         model=settings.OLLAMA_MODEL,
#         prompt=prompt
#     )["response"]


# core/llm.py

import ollama
from back.core.settings import settings

class LLM:

    def __init__(self):
        self.client = ollama.Client(host=settings.OLLAMA_HOST)
        self.model = settings.OLLAMA_MODEL

    def generate(self, prompt: str) -> str:
        response = self.client.generate(
            model=self.model,
            prompt=prompt
        )
        return response["response"]


def get_llm():
    return LLM()