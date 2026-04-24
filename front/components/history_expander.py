import streamlit as st

def _render_history_content(max_items: int = 8):
    history_items = list(reversed(st.session_state.search_history[-max_items:]))

    if not history_items:
        st.info("Belum ada riwayat percakapan.")
        return

    for i, item in enumerate(history_items, 1):
        question = item.get("question", "-")
        timestamp = item.get("timestamp", "-")
        tool = item.get("tool") or "Tanpa tool"
        model_name = item.get("model_name") or "Model tidak tercatat"

        with st.container(border=True):
            st.caption(f"#{i} • {timestamp}")
            st.markdown(f"**Q:** {question}")
            st.caption(f"Tool: {tool} | Model: {model_name}")


def render_history(max_items: int = 8, use_expander: bool = True):
    if use_expander:
        with st.expander("Riwayat", expanded=False):
            _render_history_content(max_items=max_items)
    else:
        _render_history_content(max_items=max_items)