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

def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def add_search_history(question: str, answer: str, tool_used: str | None):
    st.session_state.search_history.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "tool": tool_used,
        "answer_preview": answer[:100] + "..." if len(answer) > 100 else answer
    })