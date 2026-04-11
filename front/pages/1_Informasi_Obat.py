import streamlit as st
import json
import requests
from services.session_service import init_session
from components.sidebar import render_sidebar
from components.chat_box import render_chat_box
from components.history_expander import render_history
from components.theme import apply_custom_theme

st.set_page_config(page_title="Pharma AI Assistant", layout="wide")
apply_custom_theme()

init_session()

with st.sidebar:
    render_sidebar()

st.title("Pusat Informasi Obat & AI Assistant")
st.markdown("*Mesin pencari pintar (RAG) dan Asisten Farmasi AI. Tanya apapun terkait info obat, stok, indikasi, atau rute pemberian.*")

render_chat_box()
render_history()
