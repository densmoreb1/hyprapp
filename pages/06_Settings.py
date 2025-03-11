from helpers.connection import MySQLDatabase
from helpers.login import login
import streamlit as st
import yaml

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    authenticator.logout(location="sidebar", key="setting_logout")
    authenticator.login(location="unrendered", key="setting_logout")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.execute_query("select id from users where name = %s", (user_name,))[0][0]
else:
    st.stop()


def add_user():
    try:
        email, register_user, register_name = authenticator.register_user()
        config = st.session_state["config"]
        with open(".streamlit/config.yml", "w") as file:
            yaml.dump(config, file, default_flow_style=False)

    except Exception as e:
        st.error(e)
        st.stop()

    if register_user is not None:
        query = "select name from users"
        sql = conn.execute_query(query)
        names = [u[0] for u in sql]

        if register_user not in names:
            query = "insert into users (name) values (%s)"
            conn.execute_query(query, (register_user,))

            query = "select id from users where name = %s"
            id = conn.execute_query(query, (register_user,))[0][0]
            st.toast(f'User "{register_user}" was created with id of {id}')
        else:
            query = "select id from users where name = %s"
            id = conn.execute_query(query, (register_user,))[0][0]
            st.toast(f'User "{register_user}" already exists with id of {id}')


if st.session_state["authentication_status"]:
    authenticator = st.session_state.get("authenticator")
    try:
        if authenticator.reset_password(st.session_state["username"]):
            st.success("Password modified successfully")

            config = st.session_state["config"]
            with open(".streamlit/config.yml", "w") as file:
                yaml.dump(config, file, default_flow_style=False)

    except Exception as e:
        st.error(e)


if "admin" in st.session_state["roles"]:
    add_user()
