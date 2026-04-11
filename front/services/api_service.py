import requests
import logging

from utils.constants import ENDPOINTS

logger = logging.getLogger(__name__)

def ask_chat(question: str, user_id: str, timeout: int = 60):
    """
    Send question to Pharma AI backend dengan timeout 60 detik.
    
    Jika ask_question RAG (LLM processing), bisa membutuhkan waktu lama.
    Timeout 60 detik = cukup untuk LLM generate final answer.
    """
    payload = {
        "question": question,
        "user_id": user_id
    }
    try:
        logger.info(f"Sending request to {ENDPOINTS['chat']} with timeout={timeout}s")
        res = requests.post(ENDPOINTS["chat"], json=payload, timeout=timeout)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout after {timeout}s untuk question: {question}")
        return {"error": f"Request timeout (backend sedang proses)"}
    except requests.exceptions.ConnectionError:
        logger.error("Connection error ke API backend")
        return {"error": "Tidak bisa terhubung ke API"}
    except Exception as e:
        logger.error(f"Error in ask_chat: {str(e)}")
        return {"error": str(e)}

def check_health():
    try:
        res = requests.get(ENDPOINTS["health"], timeout=5)
        return res.status_code == 200
    except Exception:
        return False