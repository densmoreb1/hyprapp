from helpers.connection import MySQLDatabase
from helpers.login import login
import streamlit as st
import yaml
import re

# Login
if st.session_state.get("authentication_status"):
    authenticator = st.session_state.get("authenticator")
    authenticator.logout(location="sidebar", key="setting_logout")
    authenticator.login(location="unrendered", key="setting_logout")
else:
    login()

conn = MySQLDatabase()


# Get the current user
if 'username' in st.session_state and st.session_state['username'] is not None:
    user_name = st.session_state['username']
    user_id = conn.execute_query('select id from users where name = %s', (user_name,))[0][0]
else:
    st.stop()


def add_user():
    st.write('## Add a User')
    user = st.text_input('Username').lower()

    query = 'select name from users'
    sql = conn.execute_query(query)
    names = [u[0] for u in sql]

    if user != '':
        if user not in names:
            query = 'insert into users (name) values (%s)'
            conn.execute_query(query, (user,))

            query = 'select id from users where name = %s'
            id = conn.execute_query(query, (user,))[0][0]
            st.toast(f'User "{user}" was created with id of {id}')
        else:
            query = 'select id from users where name = %s'
            id = conn.execute_query(query, (user,))[0][0]
            st.toast(f'User "{user}" already exists with id of {id}')
    else:
        st.stop()


if st.session_state['authentication_status']:
    authenticator = st.session_state.get("authenticator")
    try:
        if authenticator.reset_password(st.session_state['username']):
            st.success('Password modified successfully')

            config = st.session_state['config']
            with open('.streamlit/config.yml', 'w') as file:
                yaml.dump(config, file, default_flow_style=False)

    except Exception as e:
        st.error(e)

if 'admin' in st.session_state['roles']:
    add_user()
