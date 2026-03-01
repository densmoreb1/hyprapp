from helpers.connection import MySQLDatabase
from helpers.dialogs import possible_volume
from helpers.login import login
import streamlit as st

st.write("# Create Meso")

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    if authenticator:
        authenticator.logout(location="sidebar", key="create_logout")
        authenticator.login(location="unrendered", key="create_login")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.execute_query("select id from users where name = %s", (user_name,))[
        0
    ][0]
else:
    st.stop()


# Get the available exercises
groups_sql = conn.execute_query(
    "select distinct muscle_group from exercises order by muscle_group", params=None
)
muscle_groups = [g[0] for g in groups_sql]

name = st.text_input("Name of Meso").lower()
weeks = st.selectbox("Weeks", (4, 5, 6))
days = st.selectbox("Days per week", (1, 2, 3, 4, 5, 6, 7))
old_meso_id = None


reuse = None
button_cols = st.columns([1, 7])
with button_cols[0]:
    result = st.button("Create Meso")
with button_cols[1]:
    # Get Meso for the selected User
    query = "select distinct name, meso_id from mesos where user_id = %s order by meso_id desc"
    sql = conn.execute_query(query, (user_id,))
    mesos = [g[0] for g in sql]

    if len(mesos) > 0:
        reuse = st.checkbox("Reuse Meso")

if reuse:
    meso_name = st.selectbox("Past Mesos", mesos)
    old_meso_id = conn.execute_query(
        "select meso_id from mesos where name = %s", (meso_name,)
    )[0][0]
else:
    meso_name = None


if old_meso_id is None:
    meso = {}
    cols = st.columns(days, border=True)
    for i in range(len(cols)):
        if days >= i:
            with cols[i]:
                st.write(f"### Day {i + 1}")

                exercises_per = st.selectbox(
                    label="How many exercises?",
                    options=(1, 2, 3, 4, 5, 6, 7, 8, 9),
                    key=f"per{i}{name}",
                )

                final_exercise_list = []
                for r in range(exercises_per):
                    muscle = st.selectbox(
                        label=f"Exercise {r + 1}",
                        options=muscle_groups,
                        index=None,
                        key=f"muscle{i}{r}{name}",
                        placeholder="Muscle Group",
                    )

                    sql = conn.execute_query(
                        "select name from exercises where muscle_group = %s order by name",
                        (muscle,),
                    )
                    exercise_selection = [e[0] for e in sql]
                    exercise = st.selectbox(
                        label="Exercise",
                        options=exercise_selection,
                        index=None,
                        key=f"exercise{i}{r}{name}",
                        label_visibility="collapsed",
                        placeholder="Exercise",
                    )

                    final_exercise_list.append(exercise)

                meso[i] = final_exercise_list

else:
    query = "select max(week_id) - 1 from mesos where meso_id = %s and user_id = %s"
    last_week = conn.execute_query(query, (old_meso_id, user_id))[0][0]

    query = """
            select distinct day_id
            from mesos m
            where meso_id = %s and user_id = %s and week_id = %s
            order by day_id
            """
    sql = conn.execute_query(query, (old_meso_id, user_id, last_week))

    meso = {}
    cols = st.columns(len(sql), border=True)
    for i in range(len(cols)):
        with cols[i]:
            st.write(f"### Day {i + 1}")

            query = """
                    select distinct exercise_id, order_id, e.name, e.muscle_group
                    from mesos m
                    inner join exercises e on m.exercise_id = e.id
                    where meso_id = %s and user_id = %s and week_id = %s and day_id = %s
                    order by order_id
                    """
            current_day = conn.execute_query(
                query, (old_meso_id, user_id, last_week, i)
            )

            exercises_per = st.selectbox(
                label="How many exercises?",
                options=(1, 2, 3, 4, 5, 6, 7, 8, 9),
                index=len(current_day) - 1,
                key=f"per{i}{meso_name}",
            )

            final_exercise_list = []
            for r in range(exercises_per):
                if r <= len(current_day) - 1:
                    prev_exercise_id = current_day[r][0]
                    prev_name = current_day[r][2]
                    prev_group = current_day[r][3]
                else:
                    prev_exercise_id = None
                    prev_name = None
                    prev_group = None

                if prev_group in muscle_groups:
                    index = muscle_groups.index(prev_group)
                else:
                    index = None

                muscle = st.selectbox(
                    label=f"Exercise {r + 1}",
                    options=muscle_groups,
                    index=index,
                    key=f"muscle{i}{r}{meso_name}",
                    placeholder=f"{prev_group}",
                )

                sql = conn.execute_query(
                    "select name from exercises where muscle_group = %s order by name",
                    (muscle,),
                )
                exercise_selection = [e[0] for e in sql]

                if prev_name in exercise_selection:
                    index = exercise_selection.index(prev_name)
                else:
                    index = None

                exercise = st.selectbox(
                    label="Exercise",
                    options=exercise_selection,
                    key=f"exercise{i}{r}{meso_name}",
                    index=index,
                    placeholder=f"{prev_name}",
                    label_visibility="collapsed",
                )

                final_exercise_list.append(exercise)

            meso[i] = final_exercise_list


# Create toast for possible sets in a week
possible_volume(conn, meso)

if result and name != "":

    previous_mesos = conn.execute_query(
        "select name from mesos where name = %s and user_id = %s",
        (name, user_id),
    )
    if len(previous_mesos) > 0:
        st.toast("Meso already exists with name", icon="⚠️")
        st.stop()

    meso_id = conn.execute_query(
        "select max(meso_id) from mesos where user_id = %s", (user_id,)
    )[0][0]
    if meso_id is None:
        meso_id = 0
    else:
        meso_id += 1

    for week_id in range(weeks):
        for day_id, value in meso.items():
            for order_id in range(len(value)):
                exercise_id = conn.execute_query(
                    "select id from exercises where name = %s", (value[order_id],)
                )[0][0]
                conn.insert_set(
                    meso_id=meso_id,
                    meso_name=meso_name,
                    user_id=user_id,
                    completed=0,
                    completed_day=0,
                    set_id=0,
                    reps=None,
                    weight=None,
                    order_id=order_id,
                    exercise_id=exercise_id,
                    day_id=day_id,
                    week_id=week_id,
                )

    st.toast("Meso Created", icon="✅")
