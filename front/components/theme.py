import streamlit as st

def apply_custom_theme():
    st.markdown("""
        <style>
            /* Typography additions without hardcoding color */
            h1, h2, h3 {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-weight: 600;
            }
            
            /* Buttons */
            div.stButton > button:first-child {
                border-radius: 6px;
                padding: 0.5rem 1rem;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            div.stButton > button:first-child:hover {
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            /* Metric Cards */
            div[data-testid="metric-container"] {
                padding: 1.25rem;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            }
            
            /* Inputs */
            .stTextInput>div>div>input {
                border-radius: 6px;
            }
            
            /* Info/Success/Warning boxes */
            .stAlert {
                border-radius: 6px;
                border: none;
            }
        </style>
    """, unsafe_allow_html=True)
