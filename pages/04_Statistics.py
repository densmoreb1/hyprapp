from helpers.connection import get_db
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
        authenticator.login(location="unrendered", key="stats_login")
else:
    login()

conn = get_db()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user = conn.get_user_settings(user_name)
    user_id = user[0]
    past_mesos_count = user[3]
    months = user[4]
else:
    st.stop()

primary_color = "#EF5350"
background_color = "#121212"
text_color = "#E0E0E0"
line_color = "#EF5350"

st.write("### Sets")

muscle_groups = conn.get_muscle_groups()
muscle_group = st.multiselect("Muscle Groups", muscle_groups)

# Show set increase over each meso
if len(muscle_group) != 0:
    limited_mesos_query = """
        SELECT DISTINCT meso_id
        FROM mesos
        ORDER BY meso_id DESC
        LIMIT %s
        """
    limited_mesos = conn.execute_query(limited_mesos_query, (past_mesos_count,))

    meso_ids = [x[0] for x in limited_mesos]
    placeholders = ", ".join(["%s"] * len(meso_ids))

    for muscle in muscle_group:
        sets_query = f"""
            SELECT m.name,
                   m.week_id + 1,
                   e.muscle_group,
                   COUNT(m.set_id),
                   m.meso_id
            FROM mesos m
            INNER JOIN exercises e ON m.exercise_id = e.id
            WHERE m.user_id = %s
              AND m.weight IS NOT NULL
              AND m.reps != 0
              AND m.completed = 1
              AND e.muscle_group = %s
              AND m.meso_id IN ({placeholders})
            GROUP BY m.meso_id,
                     m.name,
                     m.week_id,
                     e.muscle_group
            ORDER BY m.meso_id
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
                yaxis_title="Sets over each Meso week",
                legend_title="Mesocycle",
                bargap=0.2,
                height=500,
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, width="stretch")

            sets_query = f"""
                SELECT DATE_SUB(
                           DATE(m.date_completed),
                           INTERVAL WEEKDAY(m.date_completed) DAY
                       ) AS week_start,
                       COUNT(m.set_id)
                FROM mesos m
                INNER JOIN exercises e ON m.exercise_id = e.id
                WHERE m.user_id = %s
                  AND m.weight IS NOT NULL
                  AND m.reps != 0
                  AND m.completed = 1
                  AND e.muscle_group = %s
                  AND m.date_completed >= DATE_SUB(CURDATE(), INTERVAL %s MONTH)
                GROUP BY week_start
                ORDER BY week_start
                """
            sets_sql = conn.execute_query(sets_query, (user_id, muscle, months))
            df = pd.DataFrame(
                sets_sql,
                columns=pd.Index(["Week", "Sets"]),
            )
            fig = px.bar(
                df,
                x="Week",
                y="Sets",
                barmode="group",
                text="Sets",
            )
            fig.update_layout(
                xaxis_title="Week",
                yaxis_title="Sets per week",
                bargap=0.2,
                height=500,
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, width="stretch")

        else:
            st.write(muscle.capitalize())
            st.write("None")


st.write("### Volume")

exercise_selection = []
if muscle_group:
    exercise_selection = conn.get_exercises_by_group(muscle_group[-1])
exercise = st.selectbox(
    "Exercise",
    exercise_selection,
    index=None,
    placeholder="Exercise",
    label_visibility="collapsed",
)
if exercise:
    exercise_id = conn.get_exercise_id(exercise)

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
