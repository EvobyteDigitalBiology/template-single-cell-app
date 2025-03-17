
import streamlit as st
import requests.auth as requests_auth

import uiconfig
import extensions

# VALIDATION SESSION STATE

# Remove sidebar
st.markdown(
    """
<style>
    [data-testid="collapsedControl"] {
        display: none
    }
    [data-testid="stSidebar"] {
        display: none
    }
</style>
""",
    unsafe_allow_html=True,
)


col1, col2, col3, col4 = st.columns([1, 2, 6, 3])


with col2:
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    st.image("static/EvoLogoSmall.jpg")

with col3:
    st.title("Evobyte Case Study scRNASeq")

    # Login screen
    login_form = st.form("Login")
    login_form.subheader("Login")


username = login_form.text_input("Username").lower()
password = login_form.text_input("Password", type="password")

if login_form.form_submit_button("Login"):
    
    # Run JWT authentication after login submit
    
    if uiconfig.AUTH_METHOD == uiconfig.AUTH_METHOD.BASIC:
        try:
            authentication_status = extensions.user_auth_basic(username, password)
            if authentication_status:
                st.session_state['auth_status'] = True
                st.session_state['username'] = username
                st.session_state['httpauth'] = requests_auth.HTTPBasicAuth(username, password)
                st.rerun()
            else:
                st.error("Username/password is incorrect")
        except ValueError:
            authentication_status = False
            st.error("Error during login request")