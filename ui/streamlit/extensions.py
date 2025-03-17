# tCodeApp/extensions.py

"""

This module contains various extensions for the tCodeApp application.

Functions:
- add_navigation(): Adds navigation bars to the Streamlit app.
- validate_aa_seq(): Validates an amino acid sequence.
- user_auth_status(): Checks the authentication status of the current user.
- get_jwt_token(username: str, password: str): Retrieves a JWT token from the API.
- start_token_refresh_thread(): Starts a thread to refresh the JWT token.

"""

import threading
import time
import os
import requests

import requests
import requests.auth as requests_auth

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx

import uiconfig

APP_NAME = "app.py"

def remove_sidebar():
    # Remove sidebar
    st.markdown(
        """
    <style>
        [data-testid="collapsedControl"] {
            display: none
        }
    </style>
    """,
        unsafe_allow_html=True,
    )


def add_navigation():
    """
    Adds navigation links to the Streamlit app as navbar.
    """
    with st.container(border=True, height=400):
        st.page_link("pages/dashboard.py", label="Home")
        st.page_link("pages/projects.py", label="Projects")
        st.page_link("pages/bind.py", label="tCode Bind")
        st.page_link("pages/about.py", label="About")
        st.container(height=160, border=False)
        st.page_link("pages/logout.py", label=":surfer: :red[Logout]")

def user_auth_basic(username: str, password: str):
    
    # requets to user auth group
    login = requests_auth.HTTPBasicAuth(username, password)
    
    res = requests.get(os.path.join(uiconfig.BACKEND_API_ENDPOINT, "check_user_group/"),
                       auth=login,
                       params={"group": uiconfig.AUTH_USER_GROUP})
    
    if res.status_code == 200:
        return True
    else:
        return False


def user_auth_status():
    """
    Check the access token in the cookie and authenticate against the backend.

    Returns:
        bool: True if the user is authenticated, False otherwise.
    """
    if "access_token" in st.session_state:
        access_token = st.session_state["access_token"]
        url = os.path.join(tc_config.BACKEND_API_ENDPOINT, "token/verify/") # Needs update
        data = {"token": access_token}
        response = requests.post(url, data=data)

        if response.status_code == 200:
            return True
        else:
            return False
    else:
        return False


def get_jwt_token(username: str, password: str):
    """
    Get a JWT token from the backend API.

    Args:
        username (str): The username.
        password (str): The password.

    Returns:
        tuple: A tuple containing the access token and refresh token.

    Raises:
        ValueError: If the username or password is incorrect.
    """
    url = os.path.join(tc_config.BACKEND_API_ENDPOINT, "token/")
    data = {"username": username, "password": password}
    response = requests.post(url, data=data)

    if response.status_code == 200:
        access_token = response.json()["access"]
        refresh_token = response.json()["refresh"]

        return access_token, refresh_token
    else:
        raise ValueError("Username/password is incorrect")


def start_token_refresh_thread():
    """Start a thread to refresh the JWT token.
    
    Start a thread which periodially runs refresh_access_token
    method. Refeshes access_token of st.session_state
    
    add_script_run_ctx add thread to st script context thread.
    
    """
    
    def refresh_access_token(session_state):
        while True:
            url = os.path.join(tc_config.BACKEND_API_ENDPOINT, "token/refresh/")
            data = {"refresh": session_state["refresh_token"]}
            response = requests.post(url, json=data, verify=False)

            if response.status_code == 200:
                access_token = response.json()["access"]
                session_state["access_token"] = access_token

                time.sleep(tc_config.ACCESS_TOKEN_REFESH_SECONDS)
            else:
                raise ValueError("Could not refresh token")

    t = threading.Thread(target=refresh_access_token, args=(st.session_state,))
    add_script_run_ctx(t)
    t.start()

def check_endpoint_status(endpoint: str, auth: requests_auth.HTTPBasicAuth):
    """
    Check the status of the backend API endpoint.

    Returns:
        bool: True if the backend API endpoint is reachable, False otherwise.
    """
    try:
        response = requests.get(endpoint, auth=auth)

        if response.status_code == 200:
            return True
        else:
            return False
    except requests.exceptions.ConnectionError:
        return False