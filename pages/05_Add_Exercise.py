from helpers.connection import get_db
from helpers.login import login
import streamlit as st

st.write("# Add Exercise")

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    if authenticator:
        authenticator.logout(location="sidebar", key="add_logout")
        authenticator.login(location="unrendered", key="add_login")
else:
    login()

conn = get_db()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.get_user_settings(user_name)[0]
else:
    st.stop()


groups = conn.get_muscle_groups()

group = st.selectbox("Muscle Group", groups, index=None)
enter_name = st.text_input("Exercise Name").lower().strip()
result = st.button("Create Exercise")

names = conn.get_exercises_by_group(group)
insert_sql = """
            INSERT INTO exercises (name, muscle_group)
            VALUES (%s, %s)
            """

st.write("## Existing Exercises")
for name in names:
    st.write(name)

if result:
    if enter_name not in names:
        conn.execute_query(insert_sql, (enter_name, group))
        st.toast("Exercise created")
    else:
        st.toast("Exercise already exists")
