import streamlit as st
from datetime import datetime
import uuid

def init_session():
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "search_history" not in st.session_state:
        st.session_state.search_history = []

def add_message(role: str, content: str, model_name: str | None = None):
    payload = {"role": role, "content": content}
    if model_name:
        payload["model_name"] = model_name
    st.session_state.messages.append(payload)

def add_search_history(question: str, answer: str, tool_used: str | None, model_name: str | None = None):
    st.session_state.search_history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "tool": tool_used,
        "model_name": model_name,
        "answer_preview": answer[:100] + "..." if len(answer) > 100 else answer
    })