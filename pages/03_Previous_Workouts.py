from helpers.connection import MySQLDatabase
from helpers.login import login
import streamlit as st

st.write("# Previous Workouts")

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    if authenticator:
        authenticator.logout(location="sidebar", key="previous_logout")
        authenticator.login(location="unrendered", key="previous_logout")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.get_user_settings(user_name)[0]
else:
    st.stop()


# Get Meso for the selected User
mesos = conn.get_meso_names(user_id)


# Check if there are no mesos for this user
if len(mesos) > 0:
    meso_name = st.selectbox("Mesos", mesos)
    meso_id = conn.get_meso_id(meso_name, user_id)
else:
    st.write("Looks you have not created a meso yet")
    st.stop()


# Get the completed week_ids
query = """
        SELECT DISTINCT week_id
        FROM mesos
        WHERE meso_id = %s
            AND user_id = %s
            AND completed = 1
        ORDER BY week_id DESC
        """
sql = conn.execute_query(query, (meso_id, user_id))
weeks = [d[0] + 1 for d in sql]

if len(weeks) > 0:
    week_id = st.selectbox("Week", weeks) - 1
else:
    st.write("You have not completed a workout yet")
    st.stop()


# Get the completed day_ids
query = """
        SELECT DISTINCT day_id
        FROM mesos
        WHERE completed = 1
            AND meso_id = %s
            AND week_id = %s
            AND user_id = %s
        ORDER BY day_id
        """
sql = conn.execute_query(query, (meso_id, week_id, user_id))
days = [str(d[0] + 1) for d in sql]

day_tabs = st.tabs(days)

for day_id in range(len(day_tabs)):
    with day_tabs[day_id]:
        st.write(f"## Day {day_id + 1}")

        # Get the exercises
        query = """
                SELECT DISTINCT e.name
                    , e.id
                    , m.order_id
                FROM mesos m
                INNER JOIN exercises e ON m.exercise_id = e.id
                WHERE m.day_id = %s
                    AND m.week_id = %s
                    AND m.meso_id = %s
                    AND m.user_id = %s
                ORDER BY m.order_id
                """
        exercises = conn.execute_query(query, (day_id, week_id, meso_id, user_id))

        for i in range(len(exercises)):
            exercise_name = exercises[i][0]

            query = """
                    SELECT m.set_id
                        , m.reps
                        , m.weight
                        , e.name
                        , e.id
                        , m.order_id
                    FROM mesos m
                    INNER JOIN exercises e ON m.exercise_id = e.id
                    WHERE m.day_id = %s
                        AND m.week_id = %s
                        AND m.meso_id = %s
                        AND m.user_id = %s
                        AND e.name = %s
                    ORDER BY m.order_id
                    """
            workout = conn.execute_query(
                query, (day_id, week_id, meso_id, user_id, exercise_name)
            )

            st.write(f"### {exercise_name}")

            for i in range(len(workout)):
                set_id = workout[i][0]
                reps = workout[i][1]
                weight = workout[i][2]
                name = workout[i][3]
                exercise_id = workout[i][4]
                order_id = workout[i][5]

                cols = st.columns(3)
                with cols[0]:
                    st.write(f"Set: {set_id + 1}")
                with cols[1]:
                    st.write(f"Weight: {weight}")
                with cols[2]:
                    st.write(f"Reps: {reps}")

        if st.button(f"Reopen Day {day_id + 1}"):
            query = """
                    UPDATE mesos
                    SET completed_day = 0
                    WHERE user_id = %s
                        AND meso_id = %s
                        AND week_id = %s
                        AND day_id = %s
                    """
            conn.execute_query(query, (user_id, meso_id, week_id, day_id))
            st.switch_page("01_Current_Workout.py")


st.write("###")
if st.button("Current Workout"):
    st.switch_page("01_Current_Workout.py")

if st.button("Add a Week"):

    max_week_id = int(
        conn.execute_query(
            """
            SELECT MAX(week_id)
            FROM mesos
            WHERE user_id = %s
                AND meso_id = %s
            """,
            (user_id, meso_id),
        )[0][0]
    )

    query = """
            SELECT DISTINCT day_id
                , exercise_id
                , order_id
                , set_id
            FROM mesos
            WHERE user_id = %s
                AND meso_id = %s
                AND week_id = %s
            ORDER BY day_id, order_id
            """

    workout_week = conn.execute_query(query, (user_id, meso_id, max_week_id))

    for each_day in workout_week:
        day_id = each_day[0]
        exercise_id = each_day[1]
        order_id = each_day[2]
        set_id = each_day[3]

        conn.insert_set(
            meso_id=meso_id,
            meso_name=meso_name,
            user_id=user_id,
            completed=0,
            completed_day=0,
            set_id=set_id,
            reps=None,
            weight=None,
            order_id=order_id,
            exercise_id=exercise_id,
            day_id=day_id,
            week_id=max_week_id + 1,
        )

    st.toast(f"Week {max_week_id + 2} added", icon="✅")

if st.button("Delete Meso"):
    query = """
            DELETE
            FROM mesos
            WHERE user_id = %s
                AND meso_id = %s
            """
    conn.execute_query(query, (user_id, meso_id))
    st.toast(f"{meso_name} deleted", icon="👑")
