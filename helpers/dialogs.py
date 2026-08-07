import streamlit as st
import datetime
import random
import time


def add_or_not(pump, soreness, effort):

    if soreness <= 2:
        if effort <= 3:
            return True
    elif soreness == 3:
        if pump <= 3 and effort <= 2:
            return True

    return False


def possible_volume(conn, exercises):
    sets = {}
    for day_id, value in exercises.items():
        for order_id in range(len(value)):
            exercise_name = value[order_id]
            query = """
                    SELECT muscle_group
                    FROM exercises
                    WHERE name = %s
                    """
            sql = conn.execute_query(query, (exercise_name,))

            if sql:
                muscle_group = sql[0][0]
            else:
                return

            # On average of 3 sets per exercise per muscle_group
            if muscle_group in sets:
                sets[muscle_group] += 3
            else:
                sets[muscle_group] = 3

    sets = dict(sorted(sets.items(), key=lambda item: item[1], reverse=True))

    st.write("### Possible Sets")
    for group, count in sets.items():
        st.write(f"{group.capitalize()}: {count}")


def weekly_volume(conn, user_id, meso_id, exercise_id, week_id):
    group = conn.get_muscle_group_by_exercise_id(exercise_id)

    query = """
            SELECT COUNT(set_id)
            FROM mesos m
            INNER JOIN exercises e ON m.exercise_id = e.id
            WHERE user_id = %s
                AND meso_id = %s
                AND muscle_group = %s
                AND (
                    week_id = %s
                    OR week_id = %s
                    )
            GROUP BY week_id
            ORDER BY week_id
            """
    sql = conn.execute_query(query, (user_id, meso_id, group, week_id - 1, week_id))

    if len(sql) < 2:
        return

    last = int(sql[0][0])
    current = int(sql[1][0])

    if last > current:
        text = "↘️"
    else:
        text = "🎯"

    st.toast(f"{group.capitalize()} Last: {last} Current: {current}", icon=text)

    time.sleep(1)


@st.dialog("End Meso")
def end(conn, user_id, meso_id):
    st.write("Warning you are about to end the meso cycle early")
    st.write("This will delete sets that have not been completed")
    if st.button("Confirm"):
        query = """
                DELETE
                FROM mesos
                WHERE user_id = %s
                    AND meso_id = %s
                    AND completed = 0
                """
        conn.execute_query(query, (user_id, meso_id))

        query = """
                UPDATE mesos
                SET completed_day = 1
                WHERE user_id = %s
                    AND meso_id = %s
                """
        conn.execute_query(query, (user_id, meso_id))
        st.rerun()


@st.dialog("Score")
def enter_score(
    conn,
    meso_id,
    meso_name,
    user_id,
    day_id,
    week_id,
    max_week_id,
    group_exercises,
):

    st.write("Enter scores")

    mapping = {"None": 1, "Low": 2, "Medium": 3, "High": 4}
    if week_id != 0:
        soreness = st.segmented_control(
            "Soreness (from last workout)",
            options=mapping.keys(),
            key="sore",
        )
    else:
        soreness = "None"

    pump = st.segmented_control("Pump", options=mapping.keys(), key="pump")
    effort = st.segmented_control("Effort", options=mapping.keys(), key="effort")

    if pump and soreness and effort:
        add_set = add_or_not(mapping[pump], mapping[soreness], mapping[effort])
        st.write(add_set)

        if st.button("Enter"):
            if add_set:
                chosen = random.choice(group_exercises)
                exercise_id = chosen["exercise_id"]
                order_id = chosen["order_id"]

                max_set = conn.execute_query(
                    """
                    SELECT MAX(set_id)
                    FROM mesos
                    WHERE meso_id = %s
                        AND user_id = %s
                        AND day_id = %s
                        AND week_id = %s
                        AND exercise_id = %s
                    """,
                    (
                        meso_id,
                        user_id,
                        day_id,
                        week_id,
                        exercise_id,
                    ),
                )[0][0]
                set_id = (max_set + 1) if max_set is not None else 0

                for i in range(week_id + 1, max_week_id + 1):
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
                        week_id=i,
                    )
            st.rerun()


@st.dialog("Records")
def records(conn, user_id, exercise_id, exercise_name):
    # most volume in one set
    query = """
            SELECT MAX(weight)
                , MAX(reps)
                , date_completed
            FROM mesos
            WHERE user_id = %s
                AND completed = 1
                AND exercise_id = %s
            GROUP BY date_completed
                , exercise_id
            ORDER BY MAX(weight) * MAX(reps) DESC limit 1
            """
    sql = conn.execute_query(query, (user_id, exercise_id))
    if len(sql) == 0:
        st.write(f"No previous workouts for {exercise_name}")
        st.stop()

    reps = sql[0][1]
    weight = sql[0][0]
    date = datetime.datetime.strftime(sql[0][2], "%m/%d/%Y")

    st.write(f"### {exercise_name.capitalize()}")
    st.write(f"#### Most Volume {date}")
    st.write(f"Weight: {weight} Reps: {reps}")

    # most weight
    query = """
            SELECT MAX(weight)
                , date_completed
            FROM mesos
            WHERE user_id = %s
                AND completed = 1
                AND exercise_id = %s
            GROUP BY date_completed
                , exercise_id
            ORDER BY MAX(weight) DESC
                , date_completed DESC limit 1
            """
    sql = conn.execute_query(query, (user_id, exercise_id))
    if len(sql) == 0:
        st.write(f"No previous workouts for {exercise_name}")
        st.stop()

    weight = sql[0][0]
    date = datetime.datetime.strftime(sql[0][1], "%m/%d/%Y")

    st.write(f"#### Most Weight {date}")
    st.write(f"Weight: {weight}")


@st.dialog("Add exercise")
def add_exercise(conn, user_id, meso_id, day_id, week_id, meso_name, max_week_id):

    groups = conn.get_muscle_groups()

    group = st.selectbox("Muscle Group", groups, index=None)

    exercise_selection = conn.get_exercises_by_group(group)
    exercise = st.selectbox(
        "Exercise",
        exercise_selection,
        index=None,
        placeholder="Exercise",
        label_visibility="collapsed",
    )
    exercise_id = None
    if exercise:
        exercise_id = conn.get_exercise_id(exercise)

    query = """
            SELECT MAX(order_id)
            FROM mesos
            WHERE user_id = %s
                AND meso_id = %s
                AND day_id = %s
                AND week_id = %s
            """
    max_order_id = conn.execute_query(query, (user_id, meso_id, day_id, week_id))[0][0]

    if st.button("Confirm"):
        for i in range(week_id, max_week_id + 1):
            conn.insert_set(
                meso_id=meso_id,
                meso_name=meso_name,
                user_id=user_id,
                completed=0,
                completed_day=0,
                set_id=0,
                reps=None,
                weight=None,
                order_id=max_order_id + 1,
                exercise_id=exercise_id,
                day_id=day_id,
                week_id=i,
            )
        st.rerun()


@st.dialog("Change exercise")
def change_exercise(
    exercise_id,
    conn,
    meso_id,
    user_id,
    day_id,
    week_id,
):
    group = conn.get_muscle_group_by_exercise_id(exercise_id)
    exercise_selection = conn.get_exercises_by_group(group)

    updated_exercise = st.selectbox(
        f"{group.capitalize()} Exercises", exercise_selection
    )
    updated_exercise_id = conn.get_exercise_id(updated_exercise)

    query = """
            UPDATE mesos m
            SET m.exercise_id = %s
                , m.weight = NULL
                , m.reps = NULL
                , m.completed = 0
            WHERE m.meso_id = %s
                AND m.exercise_id = %s
                AND user_id = %s
                AND day_id = %s
                AND week_id >= %s
            """
    if st.button("Confirm"):
        conn.execute_query(
            query,
            (
                updated_exercise_id,
                meso_id,
                exercise_id,
                user_id,
                day_id,
                week_id,
            ),
        )
        st.rerun()


@st.dialog("Exercise history")
def exercise_history(exercise_id, user_id, conn, past_mesos_count):
    query = """
            SELECT DISTINCT name
                , meso_id
            FROM mesos
            WHERE exercise_id = %s
                AND user_id = %s
                AND completed = 1
            ORDER BY meso_id DESC limit %s
            """
    sql = conn.execute_query(query, (exercise_id, user_id, past_mesos_count))
    for i in range(len(sql)):
        history_meso = sql[i][0]
        st.markdown(f"## <ins>{history_meso}</ins>", unsafe_allow_html=True)

        history = """
                SELECT DISTINCT week_id
                    , day_id
                FROM mesos
                WHERE exercise_id = %s
                    AND user_id = %s
                    AND completed = 1
                    AND name = %s
                ORDER BY week_id DESC
                    , day_id DESC
                  """
        history_sql = conn.execute_query(history, (exercise_id, user_id, history_meso))

        for j in range(len(history_sql)):
            history_week = history_sql[j][0]
            history_day = history_sql[j][1]
            history_reps = """
                            SELECT reps
                                , weight
                                , set_id
                                , date_completed
                            FROM mesos
                            WHERE exercise_id = %s
                                AND user_id = %s
                                AND completed = 1
                                AND name = %s
                                AND week_id = %s
                                AND day_id = %s
                            ORDER BY set_id
                            """
            history_reps_sql = conn.execute_query(
                history_reps,
                (exercise_id, user_id, history_meso, history_week, history_day),
            )
            date = datetime.datetime.strftime(history_reps_sql[0][3], "%m/%d/%Y")

            st.write(f"### {date} Week {history_week + 1} Day {history_day + 1}")

            for h in range(len(history_reps_sql)):
                reps = history_reps_sql[h][0]
                weight = history_reps_sql[h][1]
                st.write(f"Weight: {weight} Reps: {reps}")


@st.dialog("Swap Places")
def swap_places(
    exercise_name,
    conn,
    day_id,
    meso_id,
    user_id,
    week_id,
    order_id,
):
    query = """
        SELECT DISTINCT e.name
            , order_id
            , exercise_id
        FROM mesos m
        INNER JOIN exercises e ON m.exercise_id = e.id
        WHERE user_id = %s
            AND meso_id = %s
            AND week_id = %s
            AND day_id = %s
            AND e.name != %s
        ORDER BY order_id
        """
    sql = conn.execute_query(query, (user_id, meso_id, week_id, day_id, exercise_name))
    exercises = {e[0]: e[1] for e in sql}

    new_order_name = st.selectbox(
        label="Select Exercise",
        options=list(exercises.keys()),
    )

    new_order_id = exercises[new_order_name]

    if st.button("Confirm"):
        query = """
            UPDATE mesos m
            INNER JOIN exercises e ON m.exercise_id = e.id
            SET order_id = %s
            WHERE user_id = %s
                AND meso_id = %s
                AND week_id >= %s
                AND order_id = %s
                AND e.name = %s
            """
        sql = conn.execute_query(
            query,
            (
                new_order_id,
                user_id,
                meso_id,
                week_id,
                order_id,
                exercise_name,
            ),
        )
        sql = conn.execute_query(
            query,
            (
                order_id,
                user_id,
                meso_id,
                week_id,
                new_order_id,
                new_order_name,
            ),
        )
        st.rerun()
