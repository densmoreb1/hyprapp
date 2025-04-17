import streamlit as st
import datetime
import time


def add_or_not(pump, soreness, effort):

    if soreness <= 2:
        if effort <= 3:
            return True
    elif soreness == 3:
        if pump <= 3 and effort <= 2:
            return True

    return False


def weekly_volume(conn, user_id, meso_id, exercise_id, week_id):
    query = "select muscle_group from exercises where id = %s"
    group = conn.execute_query(query, (exercise_id,))[0][0]

    query = """
            select count(set_id)
            from mesos m
            inner join exercises e on m.exercise_id = e.id
            where user_id = %s and meso_id = %s and muscle_group = %s
                and (week_id = %s or week_id = %s)
            group by week_id
            order by week_id
            """
    sql = conn.execute_query(query, (user_id, meso_id, group, week_id - 1, week_id))
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
        query = "delete from mesos where user_id = %s and meso_id = %s and completed = 0;"
        conn.execute_query(query, (user_id, meso_id))


@st.dialog("Score")
def enter_score(conn, meso_id, meso_name, user_id, set_id, order_id, exercise_id, day_id, week_id, max_week_id):

    st.write("Enter scores")

    mapping = {"None": 1, "Low": 2, "Medium": 3, "High": 4}
    if week_id != 0:
        soreness = st.segmented_control("Soreness (from last workout)", options=mapping.keys(), key="sore")
    else:
        soreness = "None"

    pump = st.segmented_control("Pump", options=mapping.keys(), key="pump")
    effort = st.segmented_control("Effort", options=mapping.keys(), key="effort")

    if pump and soreness and effort:
        add_set = add_or_not(mapping[pump], mapping[soreness], mapping[effort])
        st.write(add_set)

        if st.button("Enter"):
            if add_set:
                query = """
                        insert into mesos
                        (meso_id, name, user_id, completed, completed_day, set_id, reps, weight, order_id, exercise_id, day_id, week_id, date_created) values
                        (%s,        %s,      %s,         0,            0,     %s,   %s,     %s,       %s,          %s,     %s,      %s,      now())
                        """
                for i in range(week_id + 1, max_week_id + 1):
                    conn.execute_query(query, (meso_id, meso_name, user_id, set_id, None, None, order_id, exercise_id, day_id, i))
            st.rerun()


@st.dialog("Records")
def records(conn, user_id, meso_id, exercise_id, exercise_name):

    # most volume in one set
    query = """
            select max(weight), max(reps), date_completed
            from mesos
            where user_id = %s and completed = 1 and exercise_id = %s
            group by date_completed, exercise_id
            order by max(weight) * max(reps) desc
            limit 1
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
            select max(weight), date_completed
            from mesos
            where user_id = %s and completed = 1 and exercise_id = %s
            group by date_completed, exercise_id
            order by max(weight), date_completed desc
            limit 1
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
def add_exercise(conn, user_id, meso_id, day_id, week_id, meso_name):

    query = "select distinct muscle_group from exercises order by muscle_group"
    sql = conn.execute_query(query)
    groups = [u[0] for u in sql]

    group = st.selectbox("Muscle Group", groups, index=None)

    sql = conn.execute_query("select name from exercises where muscle_group = %s order by name", (group,))
    exercise_selection = [e[0] for e in sql]
    exercise = st.selectbox("Exercise", exercise_selection, index=None, placeholder="Exercise", label_visibility="collapsed")
    if exercise:
        exercise_id = conn.execute_query("select id from exercises where name = %s", (exercise,))[0][0]

    query = "select max(order_id) from mesos where user_id = %s and meso_id = %s and day_id = %s and week_id = %s"
    max_order_id = conn.execute_query(query, (user_id, meso_id, day_id, week_id))[0][0]

    if st.button("Confirm"):
        insert_query = """
                    insert into mesos
                    (meso_id, name, user_id, completed, set_id, reps, weight, order_id, exercise_id, day_id, week_id, date_created) values
                    (%s,        %s,      %s,        %s,     %s,   %s,     %s,       %s,          %s,     %s,      %s, now())
                    """
        conn.execute_query(insert_query, (meso_id, meso_name, user_id, 0, 0, None, None, max_order_id + 1, exercise_id, day_id, week_id))
        st.rerun()


@st.dialog("Change exercise")
def change_exercise(exercise_name, exercise_id, conn, day_id, meso_id, user_id, week_id):
    group = conn.execute_query("select muscle_group from exercises where id = %s order by muscle_group", (exercise_id,))[0][0]
    sql = conn.execute_query("select name from exercises where muscle_group = %s order by name", (group,))
    exercise_selection = [e[0] for e in sql]

    updated_exercise = st.selectbox(f"{group.capitalize()} Exercises", exercise_selection)
    updated_exercise_id = conn.execute_query("select id from exercises where name = %s", (updated_exercise,))[0][0]

    query = """
            update mesos m
            set m.exercise_id = %s, m.weight = NULL, m.reps = NULL, m.completed = 0
            where m.day_id = %s and m.meso_id = %s and m.exercise_id = %s and user_id = %s and week_id >= %s
            """
    if st.button("Confirm"):
        conn.execute_query(query, (updated_exercise_id, day_id, meso_id, exercise_id, user_id, week_id))
        st.rerun()


@st.dialog("Exercise history")
def exercise_history(exercise_name, exercise_id, user_id, conn):
    query = """
            select distinct name, meso_id
            from mesos
            where exercise_id = %s and user_id = %s and completed = 1
            order by meso_id desc
            """
    sql = conn.execute_query(query, (exercise_id, user_id))
    for i in range(len(sql)):
        history_meso = sql[i][0]
        st.markdown(f"## <ins>{history_meso}</ins>", unsafe_allow_html=True)

        history = """
                  select distinct week_id, day_id
                  from mesos
                  where exercise_id = %s and user_id = %s and completed = 1 and name = %s
                  order by week_id desc, day_id desc
                  """
        history_sql = conn.execute_query(history, (exercise_id, user_id, history_meso))

        for j in range(len(history_sql)):
            history_week = history_sql[j][0]
            history_day = history_sql[j][1]
            history_reps = """
                            select reps, weight, set_id, date_completed
                            from mesos
                            where exercise_id = %s and user_id = %s and completed = 1 and name = %s and week_id = %s and day_id = %s
                            order by set_id
                            """
            history_reps_sql = conn.execute_query(history_reps, (exercise_id, user_id, history_meso, history_week, history_day))
            date = datetime.datetime.strftime(history_reps_sql[0][3], "%m/%d/%Y")

            st.write(f"### {date} Week {history_week + 1} Day {history_day + 1}")

            for h in range(len(history_reps_sql)):
                reps = history_reps_sql[h][0]
                weight = history_reps_sql[h][1]
                st.write(f"Weight: {weight} Reps: {reps}")
