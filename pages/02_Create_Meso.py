from helpers.connection import get_db
from helpers.dialogs import possible_volume
from helpers.login import login
import random
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

conn = get_db()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.get_user_settings(user_name)[0]
else:
    st.stop()


# Get the available exercises
muscle_groups = conn.get_muscle_groups()

# Load any in-progress draft so selections survive a page refresh
draft = conn.get_meso_draft(user_id) or {}

weeks_options = (4, 5, 6)
days_options = (1, 2, 3, 4, 5, 6, 7)
draft_weeks = draft.get("weeks")
draft_days = draft.get("days")

name = st.text_input("Name of Meso", value=draft.get("name", None))
weeks = st.selectbox(
    "Weeks",
    weeks_options,
    index=weeks_options.index(draft_weeks) if draft_weeks in weeks_options else 0,
)
days = st.selectbox(
    "Days per week",
    days_options,
    index=days_options.index(draft_days) if draft_days in days_options else 0,
)


reuse = None
old_meso_id = None

button_cols = st.columns([1, 1, 1, 5])
with button_cols[0]:
    result = st.button("Create Meso")
with button_cols[1]:
    randomize = st.button("Randomize")
with button_cols[2]:
    reset = st.button("Reset")
with button_cols[3]:
    mesos = conn.get_meso_names(user_id)
    if len(mesos) > 0:
        reuse = st.checkbox("Reuse Meso")

if reuse:
    meso_name = st.selectbox("Past Mesos", mesos)
    old_meso_id = conn.get_meso_id(meso_name, user_id)
else:
    meso_name = None


if old_meso_id is None:
    prefill = draft.get("loadout", [])
    num_days = days
    save_draft = True
else:
    prefill = conn.get_meso_loadout(user_id, old_meso_id)
    num_days = len(prefill)
    save_draft = False


# use session to reset the boxes when swapping mesos or reset
st.session_state.setdefault("_loaded_meso_id", old_meso_id)
st.session_state.setdefault("_loadout_version", 0)
if old_meso_id != st.session_state["_loaded_meso_id"]:
    st.session_state["_loaded_meso_id"] = old_meso_id
    st.session_state["_loadout_version"] += 1
version = st.session_state["_loadout_version"]


if randomize:
    for i in range(num_days):
        per = st.session_state.get(f"exercise_per_day_{version}_{i}", 1)
        for r in range(per):
            muscle_key = f"muscle_group_{version}_{i}_{r}"
            exercise_key = f"exercise_{version}_{i}_{r}"

            muscle = st.session_state.get(muscle_key)
            if not muscle:  # only empty boxes
                muscle = random.choice(muscle_groups)
                st.session_state[muscle_key] = muscle

            if not st.session_state.get(exercise_key):
                options = conn.get_exercises_by_group(muscle)
                if options:
                    st.session_state[exercise_key] = random.choice(options)

if reset:
    st.session_state["_loadout_version"] += 1
    conn.delete_meso_draft(user_id)
    st.rerun()

meso = {}
loadout_to_save = []
cols = st.columns(num_days, border=True)
for i in range(len(cols)):
    with cols[i]:
        st.write(f"### Day {i + 1}")

        day_prefill = prefill[i] if i < len(prefill) else []

        exercises_per = st.selectbox(
            label="How many exercises?",
            options=(1, 2, 3, 4, 5, 6, 7, 8, 9),
            index=(len(day_prefill) - 1) if day_prefill else 0,
            key=f"exercise_per_day_{version}_{i}",
        )

        final_exercise_list = []
        slots = []
        for r in range(exercises_per):
            slot = day_prefill[r] if r < len(day_prefill) else {}
            prev_group = slot.get("group")
            prev_name = slot.get("exercise")

            if prev_group in muscle_groups:
                index = muscle_groups.index(prev_group)
            else:
                index = None

            muscle = st.selectbox(
                label=f"Exercise {r + 1}",
                options=muscle_groups,
                index=index,
                key=f"muscle_group_{version}_{i}_{r}",
                placeholder=prev_group or "Muscle Group",
            )

            exercise_selection = conn.get_exercises_by_group(muscle)

            if prev_name in exercise_selection:
                index = exercise_selection.index(prev_name)
            else:
                index = None

            exercise = st.selectbox(
                label="Exercise",
                options=exercise_selection,
                index=index,
                key=f"exercise_{version}_{i}_{r}",
                placeholder=prev_name or "Exercise",
                label_visibility="collapsed",
            )

            final_exercise_list.append(exercise)
            slots.append({"group": muscle, "exercise": exercise})

        meso[i] = final_exercise_list
        loadout_to_save.append(slots)

if save_draft:
    conn.save_meso_draft(
        user_id,
        {
            "name": name,
            "weeks": weeks,
            "days": days,
            "loadout": loadout_to_save,
        },
    )


# Create toast for possible sets in a week
possible_volume(conn, meso)

if result and name.strip():

    previous_mesos = conn.execute_query(
        """
        SELECT name
        FROM mesos
        WHERE name = %s
            AND user_id = %s
        """,
        (name, user_id),
    )
    if len(previous_mesos) > 0:
        st.toast("Meso already exists with name", icon="⚠️")
        st.stop()

    meso_id = conn.execute_query(
        """
        SELECT MAX(meso_id)
        FROM mesos
        WHERE user_id = %s
        """,
        (user_id,),
    )[0][0]
    if meso_id is None:
        meso_id = 0
    else:
        meso_id += 1

    for week_id in range(weeks):
        for day_id, value in meso.items():
            for order_id in range(len(value)):
                exercise_id = conn.get_exercise_id(value[order_id])
                conn.insert_set(
                    meso_id=meso_id,
                    meso_name=name,
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

    conn.delete_meso_draft(user_id)
    st.toast("Meso Created", icon="✅")
