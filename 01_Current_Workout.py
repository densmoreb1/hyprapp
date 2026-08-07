from helpers.connection import get_db
from helpers.dialogs import add_exercise
from helpers.dialogs import change_exercise
from helpers.dialogs import end
from helpers.dialogs import enter_score
from helpers.dialogs import exercise_history
from helpers.dialogs import records
from helpers.dialogs import weekly_volume
from helpers.dialogs import swap_places
from helpers.login import login
import streamlit as st


# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    if authenticator:
        authenticator.logout(location="sidebar", key="current_logout")
        authenticator.login(location="unrendered", key="current_login")
else:
    login()

conn = get_db()


user_id = None
# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    username = st.session_state["username"]
    user = conn.get_user_settings(username)
    user_id = user[0]
    keep_score = user[2]
    past_mesos_count = user[3]
else:
    st.stop()


# Get Meso for the selected User
query = """
        SELECT DISTINCT name
            , meso_id
        FROM mesos
        WHERE user_id = %s
            AND (completed = 0
                OR completed_day = 0)
        ORDER BY meso_id DESC
        """
sql = conn.execute_query(query, (user_id,))
mesos = [g[0] for g in sql]

if len(mesos) > 0:
    meso_name = st.selectbox("Mesos", mesos)
    meso_id = conn.get_meso_id(meso_name, user_id)
else:
    if st.button("Create a new meso here"):
        st.switch_page("pages/02_Create_Meso.py")
    st.stop()


# Get the first uncompleted workout
# Get week_id
query = """
        SELECT MIN(week_id)
        FROM mesos
        WHERE completed_day = 0
            AND meso_id = %s
            AND user_id = %s
        """
week_id = conn.execute_query(query, (meso_id, user_id))[0][0]


# Get day_id
query = """
        SELECT MIN(day_id)
        FROM mesos
        WHERE completed_day = 0
            AND meso_id = %s
            AND week_id = %s
            AND user_id = %s
        """
day_id = conn.execute_query(query, (meso_id, week_id, user_id))[0][0]


# Get the exercises
query = """
        SELECT DISTINCT e.name
            , e.id
            , m.order_id
            , e.muscle_group
        FROM mesos m
        INNER JOIN exercises e ON m.exercise_id = e.id
        WHERE m.day_id = %s
            AND m.week_id = %s
            AND m.meso_id = %s
            AND m.user_id = %s
        ORDER BY m.order_id
        """
exercises = conn.execute_query(query, (day_id, week_id, meso_id, user_id))

group_exercises = {}
for ex in exercises:
    group_exercises.setdefault(ex[3], []).append(
        {"exercise_id": ex[1], "order_id": ex[2]}
    )


# Start
st.write(f"## Week {week_id + 1} Day {day_id + 1}")


# Main Page
# Exercise loop
set_id = 0
reps = None
weight = None
exercise_id = None
order_id = None
completed = None
max_set_count = 0
max_week_id = 0
for i in range(len(exercises)):
    exercise_name = exercises[i][0]
    exercise_id = exercises[i][1]
    exercise_group = exercises[i][3]

    query = """
            SELECT m.set_id
                   , m.reps
                   , m.weight
                   , e.name
                   , e.id
                   , m.order_id
                   , m.completed
            FROM mesos m
            INNER JOIN exercises e ON m.exercise_id = e.id
            WHERE m.day_id = %s
                AND m.week_id = %s
                AND m.meso_id = %s
                AND e.name = %s
                AND m.user_id = %s
            ORDER BY m.order_id
            """
    workout = conn.execute_query(
        query,
        (
            day_id,
            week_id,
            meso_id,
            exercise_name,
            user_id,
        ),
    )
    previous = conn.execute_query(
        query,
        (
            day_id,
            week_id - 1,
            meso_id,
            exercise_name,
            user_id,
        ),
    )

    # Formatting with columns
    exercise_cols = st.columns([2, 1])
    with exercise_cols[0]:
        st.write(f"### {exercise_name}")
    with exercise_cols[1]:
        button_cols = st.columns([1, 1, 1])
        with button_cols[0]:
            if st.button("Replace", key=f"replace{exercise_name}"):
                change_exercise(
                    exercise_id,
                    conn,
                    meso_id,
                    user_id,
                    day_id,
                    week_id,
                )
        with button_cols[1]:
            if st.button("History", key=f"history{exercise_name}"):
                exercise_history(
                    exercise_id,
                    user_id,
                    conn,
                    past_mesos_count,
                )
        with button_cols[2]:
            if st.button("Records", key=f"records{exercise_name}"):
                records(conn, user_id, exercise_id, exercise_name)

    max_week_query = """
            SELECT MAX(week_id)
            FROM mesos
            WHERE meso_id = %s
                AND user_id = %s
            """
    max_week_id = conn.execute_query(max_week_query, (meso_id, user_id))[0][0]
    # Set loop
    for i in range(len(workout)):
        prev_reps = None
        prev_weight = None
        # if last workout exists
        if len(previous) > 0:
            # if set exists
            if i < len(previous) and previous[i][1] is not None:
                prev_reps = previous[i][1] + 1
                prev_weight = float(previous[i][2])

        max_set_count += 1
        set_id = workout[i][0]
        reps = workout[i][1]
        weight = workout[i][2]
        exercise_id = workout[i][4]
        order_id = workout[i][5]
        completed = workout[i][6]

        cols = st.columns(4)
        with cols[0]:
            text = ""
            if completed == 1:
                if prev_reps is not None:
                    if reps is not None:
                        prev_volume = prev_weight * (prev_reps - 1)
                        current_volume = weight * reps

                        if current_volume > prev_volume:
                            text = ":dart:"
                        else:
                            text = ":arrow_lower_right:"
                else:
                    text = ":dart:"

            st.write(f"Set: {set_id + 1} {text}")

        with cols[1]:
            if completed == 1:
                input_weight = float(weight)
            else:
                input_weight = prev_weight

            weight = st.number_input(
                "Weight",
                label_visibility="collapsed",
                placeholder=f"Weight: {prev_weight}",
                value=input_weight,
                key=f"weight{exercise_name, set_id}",
                step=0.5,
            )

        with cols[2]:
            if completed == 1:
                input_reps = reps
            else:
                input_reps = prev_reps

            reps = st.number_input(
                "Reps",
                label_visibility="collapsed",
                placeholder=f"Reps: {prev_reps}",
                value=input_reps,
                key=f"reps{exercise_name, set_id}",
                step=1,
            )

        with cols[3]:
            if (
                st.button("Complete Set", key=f"completed{exercise_name, set_id}")
                and weight is not None
                and reps is not None
            ):
                query = """
                        UPDATE mesos
                        SET reps = %s
                            , weight = %s
                            , completed = 1
                            , date_completed = now()
                        WHERE set_id = %s
                            AND day_id = %s
                            AND week_id = %s
                            AND exercise_id = %s
                            AND name = %s
                            AND user_id = %s
                        """
                conn.execute_query(
                    query,
                    (
                        reps,
                        weight,
                        set_id,
                        day_id,
                        week_id,
                        exercise_id,
                        meso_name,
                        user_id,
                    ),
                )
                last_in_group = (
                    group_exercises[exercise_group][-1]["exercise_id"] == exercise_id
                )
                if set_id + 1 == len(workout) and keep_score == 1 and last_in_group:
                    enter_score(
                        conn,
                        meso_id,
                        meso_name,
                        user_id,
                        day_id,
                        week_id,
                        max_week_id,
                        group_exercises[exercise_group],
                    )
                else:
                    st.rerun()

    # Formatting with columns
    set_cols = st.columns([2, 2, 13])
    with set_cols[0]:
        add_set = st.button("Add set", key=f"add{exercise_name, set_id}")
    with set_cols[1]:
        remove_set = st.button("Remove set", key=f"remove{exercise_name, set_id}")
    with set_cols[2]:
        swap_place = st.button("Swap Places", key=f"swap{exercise_name, set_id}")

    if remove_set:
        query = """
                DELETE
                FROM mesos
                WHERE set_id = %s
                    AND day_id = %s
                    AND week_id = %s
                    AND exercise_id = %s
                    AND name = %s
                    AND user_id = %s
                """
        for i in range(week_id, max_week_id + 1):
            conn.execute_query(
                query, (set_id, day_id, i, exercise_id, meso_name, user_id)
            )

        if week_id != 0:
            weekly_volume(conn, user_id, meso_id, exercise_id, week_id)

        st.rerun()

    if add_set:
        for i in range(week_id, max_week_id + 1):
            conn.insert_set(
                meso_id=meso_id,
                meso_name=meso_name,
                user_id=user_id,
                completed=0,
                completed_day=0,
                set_id=set_id + 1,
                reps=None,
                weight=None,
                order_id=order_id,
                exercise_id=exercise_id,
                day_id=day_id,
                week_id=i,
            )

        if week_id != 0:
            weekly_volume(conn, user_id, meso_id, exercise_id, week_id)

        st.rerun()

    if swap_place:
        swap_places(exercise_name, conn, day_id, meso_id, user_id, week_id, order_id)


if st.button("Add Exercise"):
    add_exercise(conn, user_id, meso_id, day_id, week_id, meso_name, max_week_id)

# Complete workout - navigate to previous workout page
st.write("####")

if st.button("Complete Workout"):
    query = """
            SELECT COUNT(set_id)
            FROM mesos
            WHERE day_id = %s
                AND week_id = %s
                AND meso_id = %s
                AND user_id = %s
                AND completed = 1
            """
    set_count = conn.execute_query(query, (day_id, week_id, meso_id, user_id))[0][0]

    if set_count == max_set_count:
        query = """
                UPDATE mesos
                SET completed_day = 1
                WHERE day_id = %s
                    AND week_id = %s
                    AND meso_id = %s
                    AND user_id = %s
                """
        conn.execute_query(query, (day_id, week_id, meso_id, user_id))
        st.switch_page("pages/03_Previous_Workouts.py")
    else:
        st.toast("Complete all sets", icon="⚠️")


if st.button("End Meso"):
    end(conn, user_id, meso_id)
