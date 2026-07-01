from helpers.connection import MySQLDatabase
from helpers.login import login
import streamlit as st

st.write("# Add Exercise")

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    if authenticator:
        authenticator.logout(location="sidebar", key="add_logout")
        authenticator.login(location="unrendered", key="add_logout")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.execute_query(
        """
        SELECT id
        FROM users
        WHERE name = %s
        """,
        (user_name,),
    )[0][0]
else:
    st.stop()


query = """
        SELECT DISTINCT muscle_group
        FROM exercises
        ORDER BY muscle_group
        """
sql = conn.execute_query(query, params=None)
groups = [u[0] for u in sql]

group = st.selectbox("Muscle Group", groups, index=None)
enter_name = st.text_input("Exercise Name").lower().strip()
result = st.button("Create Exercise")

query = """
        SELECT name
        FROM exercises
        WHERE muscle_group = %s
        ORDER BY name
        """
sql = conn.execute_query(query, params=(group,))
names = [u[0] for u in sql]
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
