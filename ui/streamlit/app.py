# case-scrnaseq/ui/app.py


import streamlit as st

import extensions
import uiconfig

import requests.auth as requests_auth

st.set_page_config(layout="wide", page_title="Evobyte Case Study scRNASeq")

# Define session cache for auth
if "auth_status" not in st.session_state:
    st.session_state['auth_status'] = False
    
sidebar = st.sidebar.container()

with sidebar:
    st.empty()
    st.image('static/LogoSchriftzug.png')

login_page = st.Page("app_pages/login.py", title="Login", icon=":material/login:")
logout_page = st.Page("app_pages/logout.py", title="Logout", icon=":material/logout:")
dashboard_page = st.Page("app_pages/dashboard.py", title="Dashboard")
annotation_page = st.Page("app_pages/annotation.py", title="Annotation")
metrics_page = st.Page("app_pages/metrics.py", title="Metrics")
explorer_page = st.Page("app_pages/explorer.py", title="Explorer")

if not st.session_state['auth_status']:
    pg = st.navigation([login_page])
else:
    pg = st.navigation([dashboard_page, annotation_page, metrics_page, explorer_page, logout_page])

pg.run()