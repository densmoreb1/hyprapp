from helpers.connection import fmt_date
import random
import streamlit as st
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
                    WHERE name = ?
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
            WHERE user_id = ?
                AND meso_id = ?
                AND muscle_group = ?
                AND (
                    week_id = ?
                    OR week_id = ?
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


@st.dialog("End Program")
def end(conn, user_id, meso_id):
    st.write("Warning you are about to end the program early")
    st.write("This will delete sets that have not been completed")
    if st.button("Confirm"):
        query = """
                DELETE
                FROM mesos
                WHERE user_id = ?
                    AND meso_id = ?
                    AND completed = 0
                """
        conn.execute_query(query, (user_id, meso_id))

        query = """
                UPDATE mesos
                SET completed_day = 1
                WHERE user_id = ?
                    AND meso_id = ?
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
    muscle_group,
    group_exercises,
):

    st.write("Enter scores")

    # Soreness completes the score of the last session of this group.
    last = conn.get_last_group_session(user_id, meso_id, muscle_group, week_id, day_id)

    mapping = {"None": 1, "Low": 2, "Medium": 3, "High": 4}
    if last:
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
        if st.button("Enter"):
            exercise_ids = [e["exercise_id"] for e in group_exercises]
            placeholders = ", ".join("?" * len(exercise_ids))

            with conn.transaction() as cursor:
                cursor.execute(
                    f"""
                    UPDATE mesos
                    SET pump = ?
                        , effort = ?
                    WHERE meso_id = ?
                        AND user_id = ?
                        AND week_id = ?
                        AND day_id = ?
                        AND exercise_id IN ({placeholders})
                    """,
                    (
                        mapping[pump],
                        mapping[effort],
                        meso_id,
                        user_id,
                        week_id,
                        day_id,
                        *exercise_ids,
                    ),
                )
                if last:
                    cursor.execute(
                        """
                        UPDATE mesos
                        SET soreness = ?
                        WHERE meso_id = ?
                            AND user_id = ?
                            AND week_id = ?
                            AND day_id = ?
                            AND exercise_id IN (
                                SELECT id
                                FROM exercises
                                WHERE muscle_group = ?
                            )
                        """,
                        (
                            mapping[soreness],
                            meso_id,
                            user_id,
                            last[0],
                            last[1],
                            muscle_group,
                        ),
                    )

            # Sessions scored before pump/effort were stored can't be judged.
            if (
                last
                and last[2] is not None
                and last[3] is not None
                and add_or_not(last[2], mapping[soreness], last[3])
            ):
                add_score_set(
                    conn,
                    meso_id,
                    meso_name,
                    user_id,
                    day_id,
                    week_id,
                    max_week_id,
                    muscle_group,
                    last,
                )
            st.rerun()


def add_score_set(
    conn,
    meso_id,
    meso_name,
    user_id,
    day_id,
    week_id,
    max_week_id,
    muscle_group,
    last,
):
    """
    Add a set to the last session's day slot in every workout still to come.
    Inputs:
        conn: database
        meso_id: current meso
        meso_name: current meso name
        user_id: current user
        day_id: day of the current workout
        week_id: week of the current workout
        max_week_id: last week of the meso
        muscle_group: group being scored
        last: (week_id, day_id, pump, effort) of the last session of the group
    Outputs:
        None
    """
    last_week_id, last_day_id = last[0], last[1]

    query = """
            SELECT DISTINCT m.exercise_id
                , m.order_id
            FROM mesos m
            INNER JOIN exercises e ON m.exercise_id = e.id
            WHERE m.meso_id = ?
                AND m.user_id = ?
                AND m.week_id = ?
                AND m.day_id = ?
                AND e.muscle_group = ?
            """
    sql = conn.execute_query(
        query, (meso_id, user_id, last_week_id, last_day_id, muscle_group)
    )
    exercise_id, order_id = random.choice(sql)

    for i in range(last_week_id + 1, max_week_id + 1):
        # Never touch the workout in progress or ones already done.
        if (i, last_day_id) <= (week_id, day_id):
            continue

        max_set = conn.execute_query(
            """
            SELECT MAX(set_id)
            FROM mesos
            WHERE meso_id = ?
                AND user_id = ?
                AND day_id = ?
                AND week_id = ?
                AND exercise_id = ?
            """,
            (meso_id, user_id, last_day_id, i, exercise_id),
        )[0][0]
        # The exercise may have been replaced in a later week.
        if max_set is None:
            continue

        conn.insert_set(
            meso_id=meso_id,
            meso_name=meso_name,
            user_id=user_id,
            completed=0,
            completed_day=0,
            set_id=max_set + 1,
            reps=None,
            weight=None,
            order_id=order_id,
            exercise_id=exercise_id,
            day_id=last_day_id,
            week_id=i,
        )


@st.dialog("Records")
def records(conn, user_id, exercise_id, exercise_name):
    # most volume in one set
    query = """
            SELECT weight
                , reps
                , date_completed
            FROM mesos
            WHERE user_id = ?
                AND completed = 1
                AND exercise_id = ?
            ORDER BY weight * reps DESC limit 1
            """
    sql = conn.execute_query(query, (user_id, exercise_id))
    if len(sql) == 0:
        st.write(f"No previous workouts for {exercise_name}")
        st.stop()

    reps = sql[0][1]
    weight = sql[0][0]
    date = fmt_date(sql[0][2])

    st.write(f"### {exercise_name.capitalize()}")
    st.write(f"#### Most Volume {date}")
    st.write(f"Weight: {weight} Reps: {reps}")

    # most weight
    query = """
            SELECT MAX(weight)
                , date_completed
            FROM mesos
            WHERE user_id = ?
                AND completed = 1
                AND exercise_id = ?
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
    date = fmt_date(sql[0][1])

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
            WHERE user_id = ?
                AND meso_id = ?
                AND day_id = ?
                AND week_id = ?
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
            UPDATE mesos
            SET exercise_id = ?
                , weight = NULL
                , reps = NULL
                , completed = 0
            WHERE meso_id = ?
                AND exercise_id = ?
                AND user_id = ?
                AND day_id = ?
                AND week_id >= ?
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
            WHERE exercise_id = ?
                AND user_id = ?
                AND completed = 1
            ORDER BY meso_id DESC limit ?
            """
    sql = conn.execute_query(query, (exercise_id, user_id, past_mesos_count))
    for i in range(len(sql)):
        history_meso = sql[i][0]
        st.markdown(f"## <ins>{history_meso}</ins>", unsafe_allow_html=True)

        history = """
                SELECT DISTINCT week_id
                    , day_id
                FROM mesos
                WHERE exercise_id = ?
                    AND user_id = ?
                    AND completed = 1
                    AND name = ?
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
                            WHERE exercise_id = ?
                                AND user_id = ?
                                AND completed = 1
                                AND name = ?
                                AND week_id = ?
                                AND day_id = ?
                            ORDER BY set_id
                            """
            history_reps_sql = conn.execute_query(
                history_reps,
                (exercise_id, user_id, history_meso, history_week, history_day),
            )
            date = fmt_date(history_reps_sql[0][3])

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
        WHERE user_id = ?
            AND meso_id = ?
            AND week_id = ?
            AND day_id = ?
            AND e.name != ?
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
        # The exercise name is what stops the second update re-matching rows the
        # first just moved, so both halves must run together or not at all.
        query = """
            UPDATE mesos
            SET order_id = ?
            WHERE user_id = ?
                AND meso_id = ?
                AND week_id >= ?
                AND order_id = ?
                AND exercise_id = (
                    SELECT id
                    FROM exercises
                    WHERE name = ?
                )
            """
        with conn.transaction() as cursor:
            cursor.execute(
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
            cursor.execute(
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
