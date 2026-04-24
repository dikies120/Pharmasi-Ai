import streamlit as st
from services.api_service import check_health

def render_sidebar():
    # st.markdown("## Pharma AI")
    # st.caption("Asisten farmasi dengan analisis berbasis data dan reasoning AI.")
    # st.markdown("---")

    st.markdown("#### Session")
    st.caption(f"ID: {st.session_state.user_id[:8]}...")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cek API", use_container_width=True):
            if check_health():
                st.success("API connected")
            else:
                st.error("API tidak merespons")
    with col2:
        if st.button("Reset Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.search_history = []
            st.success("Riwayat dibersihkan")

    # st.markdown("---")
    # st.markdown("#### Mode Saran")
    # st.caption("Gunakan pertanyaan spesifik untuk hasil terbaik:")
    # st.caption("- Info obat: indikasi, stok, interaksi")
    # st.caption("- Validasi pasien: sebutkan nama/MR")
    # st.caption("- Follow-up: lanjutkan tanpa ulang identitas")