import streamlit as st

assert "auth_status" in st.session_state, "Auth status not found in session state"

st.session_state['auth_status'] = False
st.rerun()