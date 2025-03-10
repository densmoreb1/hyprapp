from helpers.connection import MySQLDatabase
from helpers.login import login
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
if 'username' in st.session_state and st.session_state['username'] is not None:
    user_name = st.session_state['username']
    user_id = conn.execute_query('select id from users where name = %s', (user_name,))[0][0]
else:
    st.stop()


# Get Meso for the selected User
query = 'select distinct name, meso_id from mesos where user_id = %s and completed = 0 order by meso_id desc'
sql = conn.execute_query(query, (user_id,))
mesos = [g[0] for g in sql]

if len(mesos) > 0:
    meso_name = st.selectbox('Mesos', mesos)
    meso_id = conn.execute_query('select meso_id from mesos where name = %s and user_id = %s', (meso_name, user_id))[0][0]
else:
    if st.button('Create a new meso here'):
        st.switch_page('pages/02_Create_Meso.py')
    st.stop()


# Get the first uncompleted workout
# Get week_id
query = 'select min(week_id) from mesos where completed = 0 and meso_id = %s and user_id = %s'
week_id = conn.execute_query(query, (meso_id, user_id))[0][0]


# Get day_id
query = 'select min(day_id) from mesos where completed = 0 and meso_id = %s and week_id = %s and user_id = %s'
day_id = conn.execute_query(query, (meso_id, week_id, user_id))[0][0]


# Get the exercises
query = '''
        select distinct e.name, e.id, m.order_id
        from mesos m
        inner join exercises e on m.exercise_id = e.id
        where m.day_id = %s and m.week_id = %s and m.meso_id = %s and m.user_id = %s
        order by m.order_id
        '''
exercises = conn.execute_query(query, (day_id, week_id, meso_id, user_id))


# Start
st.write(f'## Week {week_id + 1} Day {day_id + 1}')


@st.dialog('Add exercise')
def add_exercise():

    query = 'select distinct muscle_group from exercises'
    sql = conn.execute_query(query)
    groups = [u[0] for u in sql]

    group = st.selectbox('Muscle Group', groups, index=None)

    sql = conn.execute_query('select name from exercises where muscle_group = %s', (group,))
    exercise_selection = [e[0] for e in sql]
    exercise = st.selectbox('Exercise', exercise_selection, index=None, placeholder='Exercise', label_visibility='collapsed')
    if exercise:
        exercise_id = conn.execute_query('select id from exercises where name = %s', (exercise,))[0][0]

    query = 'select max(order_id) from mesos where user_id = %s and meso_id = %s and day_id = %s and week_id = %s'
    max_order_id = conn.execute_query(query, (user_id, meso_id, day_id, week_id))[0][0]

    if st.button('Confirm'):
        insert_query = '''
                    insert into mesos
                    (meso_id, name, user_id, completed, set_id, reps, weight, order_id, exercise_id, day_id, week_id, date_created) values
                    (%s,        %s,      %s,        %s,     %s,   %s,     %s,       %s,          %s,     %s,      %s, now())
                    '''
        conn.execute_query(insert_query, (meso_id, meso_name, user_id, 0, 0, None, None, max_order_id + 1, exercise_id, day_id, week_id,))
        st.rerun()


@st.dialog('Change exercise')
def change_exercise(exercise_name, exercise_id):
    group = conn.execute_query('select muscle_group from exercises where id = %s', (exercise_id,))[0][0]
    sql = conn.execute_query('select name from exercises where muscle_group = %s', (group,))
    exercise_selection = [e[0] for e in sql]

    updated_exercise = st.selectbox(f'{group.capitalize()} Exercises', exercise_selection)
    updated_exercise_id = conn.execute_query('select id from exercises where name = %s', (updated_exercise, ))[0][0]

    query = '''
            update mesos m
            set m.exercise_id = %s, m.weight = NULL, m.reps = NULL, m.completed = 0
            where m.day_id = %s and m.meso_id = %s and m.exercise_id = %s and user_id = %s and week_id >= %s
            '''
    if st.button('Confirm'):
        conn.execute_query(query, (updated_exercise_id, day_id, meso_id, exercise_id, user_id, week_id))
        st.rerun()


@st.dialog('Exercise history')
def exercise_history(exercise_name, exercise_id):
    query = '''
            select distinct name, meso_id
            from mesos
            where exercise_id = %s and user_id = %s and completed = 1
            order by meso_id desc
            '''
    sql = conn.execute_query(query, (exercise_id, user_id))
    for i in range(len(sql)):
        history_meso = sql[i][0]
        st.markdown(f'## <ins>{history_meso}</ins>', unsafe_allow_html=True)

        history = '''
                select distinct week_id, day_id
                from mesos
                where exercise_id = %s and user_id = %s and completed = 1 and name = %s
                order by week_id desc
                '''
        history_sql = conn.execute_query(history, (exercise_id, user_id, history_meso))

        for j in range(len(history_sql)):
            history_week = history_sql[j][0]
            history_day = history_sql[j][1]
            st.write(f'### Week {history_week + 1} Day {history_day + 1}')
            history_reps = '''
                            select reps, weight, set_id
                            from mesos
                            where exercise_id = %s and user_id = %s and completed = 1 and name = %s and week_id = %s and day_id = %s
                            order by set_id
                            '''
            history_reps_sql = conn.execute_query(history_reps, (exercise_id, user_id, history_meso, history_week, history_day))
            for h in range(len(history_reps_sql)):
                reps = history_reps_sql[h][0]
                weight = history_reps_sql[h][1]
                st.write(f'Weight: {weight} Reps: {reps}')


# Main Page
# Exercise loop
for i in range(len(exercises)):
    exercise_name = exercises[i][0]
    exercise_id = exercises[i][1]

    query = '''
            select m.set_id, m.reps, m.weight, e.name, e.id, m.order_id, m.completed
            from mesos m
            inner join exercises e on m.exercise_id = e.id
            where m.day_id = %s and m.week_id = %s and m.meso_id = %s and e.name = %s and m.user_id = %s
            order by m.order_id
            '''
    workout = conn.execute_query(query, (day_id, week_id, meso_id, exercise_name, user_id))
    previous = conn.execute_query(query, (day_id, week_id - 1, meso_id, exercise_name, user_id))

    # Formatting with columns
    exercise_cols = st.columns([2, 1])
    with exercise_cols[0]:
        st.write(f'### {exercise_name}')
    with exercise_cols[1]:
        button_cols = st.columns([1, 2])
        with button_cols[0]:
            if st.button('Replace', key=f'swap{exercise_name}'):
                change_exercise(exercise_name, exercise_id)
        with button_cols[1]:
            if st.button('History', key=f'history{exercise_name}'):
                exercise_history(exercise_name, exercise_id)

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

        set_id = workout[i][0]
        reps = workout[i][1]
        weight = workout[i][2]
        exercise_id = workout[i][4]
        order_id = workout[i][5]
        completed = workout[i][6]

        cols = st.columns(4)
        with cols[0]:
            st.write(f'Set: {set_id + 1}')

        with cols[1]:
            if completed == 0:
                weight = st.number_input('Weight',
                                         label_visibility='collapsed',
                                         placeholder=f'Weight: {prev_weight}',
                                         value=prev_weight,
                                         key=f'weight{exercise_name, set_id}',
                                         step=.5)
            else:
                st.write(f'Weight: {weight}')

        with cols[2]:
            if completed == 0:
                reps = st.number_input('Reps',
                                       label_visibility='collapsed',
                                       placeholder=f'Reps: {prev_reps}',
                                       value=prev_reps,
                                       key=f'reps{exercise_name, set_id}',
                                       step=1)
            else:
                st.write(f'Reps: {reps}')

        with cols[3]:
            if completed == 0:
                box = st.checkbox('Complete', key=f'completed{exercise_name, set_id}')

                if box:
                    query = '''
                            update mesos
                            set reps = %s, weight = %s, completed = 1, date_completed = now()
                            where set_id = %s and day_id = %s and week_id = %s and exercise_id = %s and name = %s and user_id = %s
                            '''
                    conn.execute_query(query, (reps, weight, set_id, day_id, week_id, exercise_id, meso_name, user_id))

    # Formatting with columns
    set_cols = st.columns([2, 15])
    with set_cols[0]:
        add_set = st.button('Add set', key=f'add{exercise_name, set_id}')
    with set_cols[1]:
        remove_set = st.button('Remove set', key=f'remove{exercise_name, set_id}')

    if remove_set:
        query = '''
                delete from mesos
                where set_id = %s and day_id = %s and week_id = %s and exercise_id = %s and name = %s and user_id = %s
                '''
        conn.execute_query(query, (set_id, day_id, week_id, exercise_id, meso_name, user_id))
        conn.execute_query(query, (set_id, day_id, week_id + 1, exercise_id, meso_name, user_id))
        st.rerun()

    if add_set:
        query = '''
                insert into mesos
                (meso_id, name, user_id, completed, set_id, reps, weight, order_id, exercise_id, day_id, week_id, date_created) values
                (%s,        %s,      %s,         0,     %s,    %s,    %s,       %s,          %s,     %s,      %s, now())
                '''
        conn.execute_query(query, (meso_id, meso_name, user_id, set_id + 1, reps, weight, order_id, exercise_id, day_id, week_id))
        conn.execute_query(query, (meso_id, meso_name, user_id, set_id + 1, reps, weight, order_id, exercise_id, day_id, week_id + 1))
        st.rerun()


if st.button('Add Exercise'):
    add_exercise()

# Complete workout - navigate to previous workout page
st.write('####')

if st.button('Complete Workout'):
    st.switch_page('pages/03_Previous_Workouts.py')
