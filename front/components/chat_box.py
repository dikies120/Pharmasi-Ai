import streamlit as st
from services.api_service import ask_chat
from services.session_service import add_message, add_search_history


def render_chat_box():
    chat_container = st.container(height=560, border=False)

    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if msg.get("model_name"):
                    st.caption(f"Model: {msg['model_name']}")

    prompt = st.chat_input(
        "Ketik pertanyaan obat, pasien, atau validasi keamanan...",
        key="informasi_obat_chat_input",
    )

    if not prompt:
        return

    prompt = prompt.strip()
    if not prompt:
        st.warning("Pertanyaan tidak boleh kosong.")
        return

    add_message("user", prompt)

    with chat_container:
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Memproses pertanyaan dan memanggil tools yang relevan..."):
                res = ask_chat(prompt, st.session_state.user_id)
                if "error" in res:
                    answer = f"Error: {res['error']}"
                    tool_used = None
                    model_name = None
                else:
                    answer = res.get("answer", "Tidak ada jawaban")
                    tool_used = res.get("tool_used")
                    model_name = res.get("model_name")

                st.write(answer)
                if model_name:
                    st.caption(f"Model: {model_name}")
                if tool_used:
                    st.caption(f"Tool: {tool_used}")

    add_message("assistant", answer, model_name=model_name)
    add_search_history(prompt, answer, tool_used, model_name=model_name)
    st.rerun()
