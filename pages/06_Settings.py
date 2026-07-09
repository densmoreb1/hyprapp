from helpers.connection import MySQLDatabase
from helpers.login import login
import streamlit as st
import yaml

st.write("# Settings")

# Login
authenticator = None
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    if authenticator:
        authenticator.logout(location="sidebar", key="setting_logout")
        authenticator.login(location="unrendered", key="setting_login")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user = conn.get_user_settings(user_name)
    user_id = user[0]
    keep_score = user[2]
    past_mesos_count = user[3]
    months = user[4]
else:
    st.stop()


if st.session_state["authentication_status"]:

    with st.form(key="score"):
        st.write("### User Workout Settings")

        mapping = {0: "Off", 1: "On"}
        reverse_mapping = {"Off": 0, "On": 1}
        change = st.segmented_control(
            "Scoring", options=mapping.values(), default=mapping[keep_score]
        )

        if st.form_submit_button() and change:
            query = """
                    UPDATE users
                    SET keep_score = %s
                    WHERE id = %s
                    """
            conn.execute_query(query, (reverse_mapping[change], user_id))
            st.success("Updated scoring")

    with st.form(key="meso_count"):
        st.write("### User Statistics")

        new = st.number_input(
            "Number of past mesos to show:",
            value=past_mesos_count,
            step=1,
        )

        new_months = st.number_input(
            "Number of past months to show in charts:",
            value=months,
            step=1,
        )

        if st.form_submit_button():
            query = """
                    UPDATE users
                    SET past_mesos = %s
                    WHERE id = %s
                    """
            conn.execute_query(query, (new, user_id))
            query = """
                    UPDATE users
                    SET months = %s
                    WHERE id = %s
                    """
            conn.execute_query(query, (new_months, user_id))
            st.success("Updated view for past mesos")

    authenticator = st.session_state.get("authenticator")
    try:
        if authenticator and authenticator.reset_password(st.session_state["username"]):
            st.success("Password modified successfully")

            config = st.session_state["config"]
            with open(".streamlit/config.yml", "w") as file:
                yaml.dump(config, file, default_flow_style=False)

    except Exception as e:
        st.error(e)


if "admin" in st.session_state["roles"]:
    # Exercise naming
    st.write("### Rename exercises")
    groups = conn.get_muscle_groups()
    group = st.selectbox("Muscle Group", groups, index=None)
    if group:
        names = conn.get_exercises_by_group(group)
        change_name = st.selectbox("Change This Exercise", names, index=None)
        if change_name:
            change_to = st.text_input("Change To", value=change_name).lower().strip()
            update_query = """
                        UPDATE exercises
                        SET name = %s
                        WHERE name = %s
                        """
            if st.button("Change Name"):
                conn.execute_query(update_query, params=(change_to, change_name))
                st.toast("Changed")

    # New user
    try:
        register_user = None
        if authenticator:
            email, register_user, register_name = authenticator.register_user()
            config = st.session_state["config"]
            with open(".streamlit/config.yml", "w") as file:
                yaml.dump(config, file, default_flow_style=False)

    except Exception as e:
        st.error(e)
        st.stop()

    if register_user is not None:
        query = """
                SELECT name
                FROM users
                """
        sql = conn.execute_query(query, params=None)
        names = [u[0] for u in sql]

        if register_user not in names:
            query = """
                    INSERT INTO users (name)
                    VALUES (%s)
                    """
            conn.execute_query(query, (register_user,))

            id = conn.get_user_settings(register_user)[0]
            st.toast(f'User "{register_user}" was created with id of {id}')
        else:
            id = conn.get_user_settings(register_user)[0]
            st.toast(f'User "{register_user}" already exists with id of {id}')
