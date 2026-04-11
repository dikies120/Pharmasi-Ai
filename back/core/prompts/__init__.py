import os

_PROMPT_DIR = os.path.dirname(__file__)

def load_prompt(prompt_name: str) -> str:
    prompt_path = os.path.join(_PROMPT_DIR, f"{prompt_name}.txt")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

SYSTEM_PROMPT = load_prompt("system_prompt")
FINAL_ANSWER_PROMPT = load_prompt("final_answer_prompt")
ANALYTICS_PROMPT = load_prompt("analytics_prompt")
