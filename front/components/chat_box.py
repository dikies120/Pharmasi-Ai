import streamlit as st
from services.api_service import ask_chat
from services.session_service import add_message, add_search_history

def render_chat_box():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    prompt = st.chat_input("Tanya apapun tentang obat...")

    if prompt:
        add_message("user", prompt)
        with st.chat_message("assistant"):
            # Loading state dengan informasi lebih detail
            with st.spinner("🔄 Memproses pertanyaan...\n(Jika ask_question, tunggu AI berpikir)"):
                res = ask_chat(prompt, st.session_state.user_id)
                if "error" in res:
                    answer = f"⚠️ Error: {res['error']}"
                    tool_used = None
                else:
                    answer = res.get("answer", "Tidak ada jawaban")
                    tool_used = res.get("tool_used")

                st.write(answer)
                add_message("assistant", answer)
                add_search_history(prompt, answer, tool_used)