from helpers.connection import MySQLDatabase
from helpers.login import login
import streamlit as st
import pandas as pd

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    authenticator.logout(location="sidebar", key="stats_logout")
    authenticator.login(location="unrendered", key="stats_logout")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.execute_query("select id from users where name = %s", (user_name,))[0][0]
else:
    st.stop()


st.write("# Statistics")

groups_sql = conn.execute_query("select distinct muscle_group from exercises")
muscle_groups = [g[0] for g in groups_sql]
muscle_groups = st.multiselect("Muscle Groups", muscle_groups)

# Get Meso for the selected User
query = "select distinct name, meso_id from mesos where user_id = %s and completed = 1 order by meso_id desc"
sql = conn.execute_query(query, (user_id,))
mesos = [g[0] for g in sql]

# Show set increase over each meso
if len(muscle_groups) != 0:
    for meso_name in mesos:

        st.write(f" ### {meso_name}")

        for muscle in muscle_groups:
            sets_query = """
            select m.name, m.week_id + 1, e.muscle_group, count(m.set_id), m.meso_id
            from mesos m
            inner join exercises e on m.exercise_id = e.id
            where user_id = %s and weight is not null and completed = 1 and m.name = %s and e.muscle_group = %s
            group by m.name, m.week_id, e.muscle_group, m.meso_id
            order by m.meso_id
            """
            sets_sql = conn.execute_query(sets_query, (user_id, meso_name, muscle))

            if len(sets_sql) > 0:
                st.write(muscle.capitalize())
                df = pd.DataFrame(sets_sql, columns=["meso_name", "Week", "muscle_group", "Sets", "meso_id"])
                df = df[df["muscle_group"] == muscle]
                st.bar_chart(df, x="Week", y="Sets")
            else:
                st.write(muscle.capitalize())
                st.write("None")
