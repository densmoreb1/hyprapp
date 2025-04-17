from helpers.connection import MySQLDatabase
from helpers.login import login
import streamlit as st

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    authenticator.logout(location="sidebar", key="add_logout")
    authenticator.login(location="unrendered", key="add_logout")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.execute_query("select id from users where name = %s", (user_name,))[0][0]
else:
    st.stop()


st.write("# Add Exercise")

query = "select distinct muscle_group from exercises order by muscle_group"
sql = conn.execute_query(query)
groups = [u[0] for u in sql]

name = st.text_input("Exercise Name").lower()
group = st.selectbox("Muscle Group", groups, index=None)
result = st.button("Create Exercise")

query = "select name from exercises"
sql = conn.execute_query(query)
names = [u[0] for u in sql]

insert_sql = "insert into exercises (name, muscle_group) values (%s, %s)"

if result:
    if name not in names:
        conn.execute_query(insert_sql, (name, group))
        st.toast("Exercise created")
    else:
        st.toast("Exercise already exists")
