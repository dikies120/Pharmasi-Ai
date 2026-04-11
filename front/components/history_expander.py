import streamlit as st

def render_history():
    with st.expander("History"):
        if not st.session_state.search_history:
            st.info("Belum ada riwayat")
        else:
            for i, item in enumerate(st.session_state.search_history, 1):
                col1, col2, col3 = st.columns([1,3,1])
                with col1:
                    st.caption(f"#{i}")
                with col2:
                    st.caption(f"**Q:** {item['question']}")
                    st.caption(f"*{item['timestamp']}*")
                    if item['tool']:
                        st.caption(f"Tool: `{item['tool']}`")
                with col3:
                    st.caption("📌")