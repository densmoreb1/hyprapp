from helpers.connection import MySQLDatabase
from helpers.login import login
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import pandas as pd

st.write("# Statistics")

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    if authenticator:
        authenticator.logout(location="sidebar", key="stats_logout")
        authenticator.login(location="unrendered", key="stats_logout")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    sql = conn.execute_query(
        "select id, past_mesos, months from users where name = %s", (user_name,)
    )
    user_id = sql[0][0]
    past_mesos_count = sql[0][1]
    months = sql[0][2]
else:
    st.stop()

primary_color = "#EF5350"
background_color = "#121212"
text_color = "#E0E0E0"
line_color = "#EF5350"


st.write("### Sets")
groups_sql = conn.execute_query(
    "select distinct muscle_group from exercises order by muscle_group", params=None
)
muscle_groups = [g[0] for g in groups_sql]
muscle_group = st.multiselect("Muscle Groups", muscle_groups)

# Show set increase over each meso
if len(muscle_group) != 0:
    limited_mesos_query = """
    select distinct meso_id
    from mesos
    order by meso_id desc
    limit %s
    """
    limited_mesos = conn.execute_query(limited_mesos_query, (past_mesos_count,))

    meso_ids = [x[0] for x in limited_mesos]
    placeholders = ", ".join(["%s"] * len(meso_ids))

    for muscle in muscle_group:
        sets_query = f"""
        select m.name, m.week_id + 1, e.muscle_group, count(m.set_id), m.meso_id
        from mesos m
        inner join exercises e on m.exercise_id = e.id
        where user_id = %s and weight is not null and reps != 0 and completed = 1 and e.muscle_group = %s and m.meso_id in ({placeholders})
        group by m.meso_id, m.name, m.week_id, e.muscle_group
        order by m.meso_id
        """
        params = [user_id, muscle] + meso_ids
        sets_sql = conn.execute_query(sets_query, tuple(params))

        if len(sets_sql) > 0:
            st.write(muscle.capitalize())
            df = pd.DataFrame(
                sets_sql,
                columns=pd.Index(
                    ["MesoName", "Week", "muscle_group", "Sets", "meso_id"]
                ),
            )

            fig = px.bar(
                df,
                x="Week",
                y="Sets",
                color="MesoName",
                barmode="group",  # or "stack"
                text="Sets",
            )

            fig.update_layout(
                xaxis_title="Week",
                yaxis_title="Sets",
                legend_title="Mesocycle",
                bargap=0.2,
                height=500,
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, width="stretch")

        else:
            st.write(muscle.capitalize())
            st.write("None")

st.write("### Volume")

group = st.selectbox("Muscle Group", muscle_groups, index=None)

sql = conn.execute_query(
    "select name from exercises where muscle_group = %s order by name", (group,)
)
exercise_selection = [e[0] for e in sql]
exercise = st.selectbox(
    "Exercise",
    exercise_selection,
    index=None,
    placeholder="Exercise",
    label_visibility="collapsed",
)
if exercise:
    exercise_id = conn.execute_query(
        "select id from exercises where name = %s", (exercise,)
    )[0][0]

    query = """
            SELECT reps, weight, workout_date
            FROM (
                SELECT
                    reps,
                    weight,
                    DATE(date_completed) AS workout_date,
                    ROW_NUMBER() OVER (
                        PARTITION BY DATE(date_completed)
                        ORDER BY reps * weight DESC
                    ) AS rn
                FROM mesos
                WHERE user_id = %s
                    AND exercise_id = %s
                    AND completed = 1
                    AND reps != 0
                    AND date_completed >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
            ) ranked
            WHERE rn = 1
            ORDER BY workout_date;
            """
    sql = conn.execute_query(query, (user_id, exercise_id, months))

    if len(sql) > 0:
        df = pd.DataFrame(sql, columns=pd.Index(["reps", "weight", "date"]))
        df["date"] = pd.to_datetime(df["date"])
        df["reps"] = df["reps"].astype("float")
        df["weight"] = df["weight"].astype("float")
        df["volume"] = df["reps"] * df["weight"]

        df["reps"] = df["reps"].astype("str")
        df["weight"] = df["weight"].astype("str")
        df["label"] = df["weight"] + " x " + df["reps"]

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

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Top Set Volume",
            hovermode="x unified",
        )
        st.plotly_chart(fig)

    else:
        st.write("None")

    query = """
            SELECT SUM(reps * weight)
                , DATE(date_completed)
            FROM mesos
            WHERE user_id = %s
                AND exercise_id = %s
                AND completed = 1
                AND reps != 0
                AND date_completed >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
            GROUP BY DATE(date_completed)
            """
    sql = conn.execute_query(query, (user_id, exercise_id, months))

    if len(sql) > 0:
        df = pd.DataFrame(sql, columns=pd.Index(["volume", "date"]))
        df["date"] = pd.to_datetime(df["date"])

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["volume"],
                mode="lines+markers",
                name="Total",
                marker=dict(color=primary_color, size=10),
                line=dict(color=line_color, width=2),
                hoverinfo="x+y+name",
            )
        )

        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Total Volume",
            hovermode="x unified",
        )

        st.plotly_chart(fig)

    else:
        st.write("None")
