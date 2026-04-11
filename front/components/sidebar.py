import streamlit as st
from services.api_service import check_health

def render_sidebar():
    st.title("Pharma AI")
    st.divider()
    
    st.subheader("User Info")
    st.caption(f"User ID: `{st.session_state.user_id[:8]}...`")
    st.divider()

    if st.button("Check API Status"):
        if check_health():
            st.success("API Connected")
        else:
            st.error("API tidak merespons")
    
    st.divider()
    
    st.subheader("Settings")
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.search_history = []
        st.success("History cleared!")