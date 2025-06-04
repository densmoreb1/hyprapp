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
    sql = conn.execute_query("select id, keep_score, past_mesos from users where name = %s", (user_name,))
    user_id = sql[0][0]
    keep_score = sql[0][1]
    past_mesos_count = sql[0][2]
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

    with st.form(key="score"):
        mapping = {0: "Off", 1: "On"}
        reverse_mapping = {"Off": 0, "On": 1}

        st.write("### User Workout Settings")

        change = st.segmented_control("Scoring", options=mapping.values(), default=mapping[keep_score])

        if st.form_submit_button():
            query = "update users set keep_score = %s where id = %s"
            conn.execute_query(query, (reverse_mapping[change], user_id))
            st.success("Updated scoring")

    with st.form(key="meso_count"):
        st.write("### User Past Meso Count")

        new = st.number_input(
            "Number of past mesos to show:",
            value=past_mesos_count,
            step=1,
        )

        if st.form_submit_button():
            query = "update users set past_mesos = %s where id = %s"
            conn.execute_query(query, (new, user_id))
            st.success("Updated view for past mesos")

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
