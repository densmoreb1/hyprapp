from helpers.connection import MySQLDatabase
from helpers.login import login
from helpers.dialogs import exercise_history
from helpers.dialogs import change_exercise
from helpers.dialogs import add_exercise
from helpers.dialogs import records
import streamlit as st

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    authenticator.logout(location="sidebar", key="current_logout")
    authenticator.login(location="unrendered", key="current_logout")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.execute_query("select id from users where name = %s", (user_name,))[0][0]
else:
    st.stop()


# Get Meso for the selected User
query = "select distinct name, meso_id from mesos where user_id = %s and completed = 0 order by meso_id desc"
sql = conn.execute_query(query, (user_id,))
mesos = [g[0] for g in sql]

if len(mesos) > 0:
    meso_name = st.selectbox("Mesos", mesos)
    meso_id = conn.execute_query("select meso_id from mesos where name = %s and user_id = %s", (meso_name, user_id))[0][0]
else:
    if st.button("Create a new meso here"):
        st.switch_page("pages/02_Create_Meso.py")
    st.stop()


# Get the first uncompleted workout
# Get week_id
query = "select min(week_id) from mesos where completed_day = 0 and meso_id = %s and user_id = %s"
week_id = conn.execute_query(query, (meso_id, user_id))[0][0]


# Get day_id
query = "select min(day_id) from mesos where completed_day = 0 and meso_id = %s and week_id = %s and user_id = %s"
day_id = conn.execute_query(query, (meso_id, week_id, user_id))[0][0]


# Get the exercises
query = """
        select distinct e.name, e.id, m.order_id
        from mesos m
        inner join exercises e on m.exercise_id = e.id
        where m.day_id = %s and m.week_id = %s and m.meso_id = %s and m.user_id = %s
        order by m.order_id
        """
exercises = conn.execute_query(query, (day_id, week_id, meso_id, user_id))


# Start
st.write(f"## Week {week_id + 1} Day {day_id + 1}")


# Main Page
# Exercise loop
max_set_count = 0
for i in range(len(exercises)):
    exercise_name = exercises[i][0]
    exercise_id = exercises[i][1]

    query = """
            select m.set_id, m.reps, m.weight, e.name, e.id, m.order_id, m.completed
            from mesos m
            inner join exercises e on m.exercise_id = e.id
            where m.day_id = %s and m.week_id = %s and m.meso_id = %s and e.name = %s and m.user_id = %s
            order by m.order_id
            """
    workout = conn.execute_query(query, (day_id, week_id, meso_id, exercise_name, user_id))
    previous = conn.execute_query(query, (day_id, week_id - 1, meso_id, exercise_name, user_id))

    # Formatting with columns
    exercise_cols = st.columns([2, 1])
    with exercise_cols[0]:
        st.write(f"### {exercise_name}")
    with exercise_cols[1]:
        button_cols = st.columns([1, 1, 1])
        with button_cols[0]:
            if st.button("Replace", key=f"swap{exercise_name}"):
                change_exercise(exercise_name, exercise_id, conn, day_id, meso_id, user_id, week_id)
        with button_cols[1]:
            if st.button("History", key=f"history{exercise_name}"):
                exercise_history(exercise_name, exercise_id, user_id, conn)
        with button_cols[2]:
            if st.button("Records", key=f"records{exercise_name}"):
                records(conn, user_id, meso_id, exercise_id, exercise_name)

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

                        if current_volume >= prev_volume:
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
            # if completed == 0:
            if st.button("Complete Set", key=f"completed{exercise_name, set_id}"):
                query = """
                        update mesos
                        set reps = %s, weight = %s, completed = 1, date_completed = now()
                        where set_id = %s and day_id = %s and week_id = %s and exercise_id = %s and name = %s and user_id = %s
                        """
                conn.execute_query(query, (reps, weight, set_id, day_id, week_id, exercise_id, meso_name, user_id))
                st.rerun()

    # Formatting with columns
    set_cols = st.columns([2, 15])
    with set_cols[0]:
        add_set = st.button("Add set", key=f"add{exercise_name, set_id}")
    with set_cols[1]:
        remove_set = st.button("Remove set", key=f"remove{exercise_name, set_id}")

    max_week_query = "select max(week_id) from mesos where meso_id = %s and user_id = %s"
    max_week_id = conn.execute_query(max_week_query, (meso_id, user_id))[0][0]
    if remove_set:
        query = """
                delete from mesos
                where set_id = %s and day_id = %s and week_id = %s and exercise_id = %s and name = %s and user_id = %s
                """
        for i in range(week_id, max_week_id + 1):
            conn.execute_query(query, (set_id, day_id, i, exercise_id, meso_name, user_id))

        st.rerun()

    if add_set:
        query = """
                insert into mesos
                (meso_id, name, user_id, completed, completed_day, set_id, reps, weight, order_id, exercise_id, day_id, week_id, date_created) values
                (%s,        %s,      %s,         0,            0,     %s,   %s,     %s,       %s,          %s,     %s,      %s,      now())
                """
        for i in range(week_id, max_week_id + 1):
            conn.execute_query(query, (meso_id, meso_name, user_id, set_id + 1, reps, weight, order_id, exercise_id, day_id, i))

        st.rerun()


if st.button("Add Exercise"):
    add_exercise(conn, user_id, meso_id, day_id, week_id, meso_name)

# Complete workout - navigate to previous workout page
st.write("####")

if st.button("Complete Workout"):
    query = """
            select count(set_id)
            from mesos
            where day_id = %s and week_id = %s and meso_id = %s and user_id = %s and completed = 1
            """
    set_count = conn.execute_query(query, (day_id, week_id, meso_id, user_id))[0][0]

    if set_count == max_set_count:

        query = """
                update mesos
                set completed_day = 1
                where day_id = %s and week_id = %s and meso_id = %s and user_id = %s
                """
        conn.execute_query(query, (day_id, week_id, meso_id, user_id))
        st.switch_page("pages/03_Previous_Workouts.py")
    else:
        st.toast("Complete all sets", icon="⚠️")
