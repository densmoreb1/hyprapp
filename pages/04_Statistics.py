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

sets_query = """
select
    e.muscle_group,
    count(m.set_id) AS set_count,
    row_number() over (partition by e.muscle_group,
                        m.meso_id order by m.week_id) AS week_rank
from mesos m
inner join exercises e on m.exercise_id = e.id
inner join users u on m.user_id = u.id
where m.completed = 1
    and u.id = %s
group by e.muscle_group, m.meso_id, m.week_id
"""

sets_sql = conn.execute_query(sets_query, (user_id,))

for muscle in muscle_groups:
    st.write(muscle.capitalize())
    df = pd.DataFrame(sets_sql, columns=["muscle_group", "set_count", "week"])
    df = df[df["muscle_group"] == muscle]
    st.bar_chart(df, x="week", y="set_count")

# view volume of exercise over each workout
