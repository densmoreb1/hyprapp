from helpers.connection import MySQLDatabase
from helpers.login import login
import pandas as pd
import streamlit as st

st.write("# Export Workouts")

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    if authenticator:
        authenticator.logout(location="sidebar", key="current_logout")
        authenticator.login(location="unrendered", key="current_login")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if "username" in st.session_state and st.session_state["username"] is not None:
    user_name = st.session_state["username"]
    user_id = conn.get_user_settings(user_name)[0]
else:
    st.stop()


# Get Mesos for the selected User
mesos = ["All"] + conn.get_meso_names(user_id)

# Check if there are no mesos for this user
meso_id = None
if len(mesos) > 0:
    meso_name = st.selectbox("Mesos", mesos)
    if meso_name != "All":
        meso_id = conn.get_meso_id(meso_name, user_id)
else:
    st.write("Looks you have not created a meso yet")
    st.stop()

if meso_name == "All":
    sql = """
        SELECT m.name meso_name
            , m.date_completed
            , week_id + 1 week
            , day_id + 1 day
            , set_id + 1 set_id
            , reps
            , weight
            , e.name exercise_name
        FROM mesos m
        INNER JOIN exercises e ON m.exercise_id = e.id
        WHERE user_id = %s
        ORDER BY meso_id, week_id, day_id, order_id
        """
    workouts = conn.execute_query(sql, (user_id,))
    filename = "all-workouts.csv"
else:
    sql = """
        SELECT m.name meso_name
            , m.date_completed
            , week_id + 1 week
            , day_id + 1 day
            , set_id + 1 set_id
            , reps
            , weight
            , e.name exercise_name
        FROM mesos m
        INNER JOIN exercises e ON m.exercise_id = e.id
        WHERE user_id = %s
            AND meso_id = %s
        ORDER BY meso_id, week_id, day_id, order_id
        """
    workouts = conn.execute_query(sql, (user_id, meso_id))
    meso_name = str(meso_name)
    filename = f"{"".join(meso_name.split(" "))}.csv"

df = pd.DataFrame(
    workouts,
    columns=pd.Index(
        [
            "meso_name",
            "date_completed",
            "week",
            "day",
            "set",
            "reps",
            "weight",
            "exercise_name",
        ]
    ),
)

st.write("## Data Preview")
st.dataframe(df.head(20))

csv = df.to_csv(header=True).encode("utf-8")
st.download_button(
    label="Download CSV",
    data=csv,
    file_name=filename,
)
