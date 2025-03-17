import streamlit as st

assert "username" in st.session_state, "Username not found in session state"
assert "auth_status" in st.session_state, "Auth status not found in session state"

st.write(f"Welcome {st.session_state['username']}")