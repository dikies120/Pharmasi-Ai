import streamlit as st
from services.session_service import init_session
from components.sidebar import render_sidebar
from components.chat_box import render_chat_box
from components.history_expander import render_history
from components.theme import apply_custom_theme

st.set_page_config(page_title="Insight AI", layout="wide")
apply_custom_theme()

init_session()

with st.sidebar:
    render_sidebar()
    st.markdown("---")
    st.subheader("Riwayat")
    st.caption(f"Total: {len(st.session_state.search_history)}")
    render_history(max_items=8, use_expander=False)

st.title("Pusat Informasi Obat & AI Assistant")
st.caption("Tanyakan informasi obat, interaksi, stok, atau validasi keamanan pasien.")
render_chat_box()
