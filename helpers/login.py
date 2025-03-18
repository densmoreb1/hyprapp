import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader


def login():
    st.set_page_config(layout="wide")

    with open(".streamlit/config.yml") as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config["credentials"], config["cookie"]["name"], config["cookie"]["key"], config["cookie"]["expiry_days"]
    )

    st.session_state["authenticator"] = authenticator
    st.session_state["config"] = config

    try:
        authenticator.login()
    except Exception as e:
        st.error(e)

    if st.session_state["authentication_status"]:
        authenticator.logout(location="sidebar", key="logout-app-home")
    elif st.session_state["authentication_status"] is False:
        st.error("Username/password is incorrect")
