from helpers.connection import MySQLDatabase
from helpers.login import login
import plotly.graph_objects as go
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


st.write("### Sets")
groups_sql = conn.execute_query("select distinct muscle_group from exercises")
muscle_groups = [g[0] for g in groups_sql]
muscle_groups = st.multiselect("Muscle Groups", muscle_groups)

# Show set increase over each meso
if len(muscle_groups) != 0:
    # Get Meso for the selected User
    query = "select distinct name, meso_id from mesos where user_id = %s and completed = 1 order by meso_id desc"
    sql = conn.execute_query(query, (user_id,))
    mesos = [g[0] for g in sql]

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

st.write("### Volume")

query = "select distinct muscle_group from exercises"
sql = conn.execute_query(query)
groups = [u[0] for u in sql]

group = st.selectbox("Muscle Group", groups, index=None)

sql = conn.execute_query("select name from exercises where muscle_group = %s", (group,))
exercise_selection = [e[0] for e in sql]
exercise = st.selectbox("Exercise", exercise_selection, index=None, placeholder="Exercise", label_visibility="collapsed")
if exercise:
    exercise_id = conn.execute_query("select id from exercises where name = %s", (exercise,))[0][0]

    query = """
            select max(reps), max(weight), date(date_completed)
            from mesos
            where user_id = %s and exercise_id = %s and completed = 1
            group by date(date_completed)
            order by date(date_completed)
            """
    sql = conn.execute_query(query, (user_id, exercise_id))

    if len(sql) > 0:
        st.write(exercise.capitalize())
        df = pd.DataFrame(sql, columns=["reps", "weight", "date"])
        df["date"] = pd.to_datetime(df["date"])
        df["volume"] = df["reps"] * df["weight"]  # Total volume
        df["label"] = df["reps"].astype(str) + " x " + df["weight"].astype(str)  # e.g. "10 x 165"

        # Plotly chart
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["volume"],
                mode="lines+markers",
                name="Total Volume",
                line=dict(color="green", width=3),
                hovertext=df["label"],  # Show "10 x 165" on hover
                hoverinfo="text+name+y+x",  # Customize hover: text + point info
            )
        )

        fig.update_layout(
            title="Training Volume Over Time", xaxis_title="Date", yaxis_title="Volume (Reps × Weight)", hovermode="x unified"
        )

        st.plotly_chart(fig)

    else:
        st.write(exercise.capitalize())
        st.write("None")
