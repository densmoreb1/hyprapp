from helpers.connection import MySQLDatabase
from helpers.login import login
import plotly.graph_objects as go
import plotly.express as px
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

primary_color = "#EF5350"
background_color = "#121212"
text_color = "#E0E0E0"
line_color = "#EF5350"

st.write("# Statistics")


st.write("### Sets")
groups_sql = conn.execute_query("select distinct muscle_group from exercises")
muscle_groups = [g[0] for g in groups_sql]
muscle_groups = st.multiselect("Muscle Groups", muscle_groups)

# Show set increase over each meso
if len(muscle_groups) != 0:
    for muscle in muscle_groups:
        sets_query = """
        select m.name, m.week_id + 1, e.muscle_group, count(m.set_id), m.meso_id
        from mesos m
        inner join exercises e on m.exercise_id = e.id
        where user_id = %s and weight is not null and completed = 1 and e.muscle_group = %s
        group by m.meso_id, m.name, m.week_id, e.muscle_group
        order by m.meso_id
        """
        sets_sql = conn.execute_query(sets_query, (user_id, muscle))

        if len(sets_sql) > 0:
            st.write(muscle.capitalize())
            df = pd.DataFrame(sets_sql, columns=["MesoName", "Week", "muscle_group", "Sets", "meso_id"])

            fig = px.bar(
                df,
                x="Week",
                y="Sets",
                color="MesoName",
                barmode="group",  # or "stack"
                text="Sets",
            )

            fig.update_layout(xaxis_title="Week", yaxis_title="Sets", legend_title="Mesocycle", bargap=0.2, height=500)
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

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
        df = pd.DataFrame(sql, columns=["reps", "weight", "date"])
        df["date"] = pd.to_datetime(df["date"])
        df["volume"] = df["reps"].astype("float") * df["weight"].astype("float")  # Total volume
        df["label"] = df["weight"].astype(str) + " x " + df["reps"].astype(str)  # e.g. "10 x 165"

        # Plotly chart
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["volume"],
                mode="lines+markers",
                name="Total Volume",
                marker=dict(color=primary_color, size=10),
                line=dict(color=line_color, width=2),
                hovertext=df["label"],  # Show "10 x 165" on hover
                hoverinfo="text+name+y+x",  # Customize hover: text + point info
            )
        )

        fig.update_layout(xaxis_title="Date", yaxis_title="Volume (Reps × Weight)", hovermode="x unified")
        st.plotly_chart(fig)

    else:
        st.write("None")
