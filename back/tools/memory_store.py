MEMORY_STORE = {}


def get_history(user_id: str):
    return MEMORY_STORE.get(user_id, [])


def save_message(user_id: str, role: str, content: str):
    MEMORY_STORE.setdefault(user_id, []).append({
        "role": role,
        "content": content
    })


def get_context(user_id: str, limit: int = 5):
    history = get_history(user_id)
    return "\n".join([
        f"{h['role']}: {h['content']}" for h in history[-limit:]
    ])