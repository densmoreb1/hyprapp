# HyprApp

## Introduction

Python / Streamlit web app

- Tracks workouts
- Able to create custom programs
- Website that works on mobile and desktop

## Setup

### Quickstart

```sh
git clone https://github.com/densmoreb1/hyprapp.git
cd hyprapp
cp .env.example .env
cp .streamlit/config.yml.example .streamlit/config.yml
```

- Change the `.env` file
  - change the `DB_PASSWORD`

```sh
docker compose up -d
```

Website is be available at `http://localhost:8501`

Login:

- username: test
- password: testing123

## User Management

### Adding a User

The web app uses [`streamlit-authenticator`](https://github.com/mkhorasani/Streamlit-Authenticator)
and `.streamlit/config.yml` to control users.

To add a username:

- Navigate to the Settings page
- Fill out the form
- Hit `Register`

A user is inserted into the database
and the `config.yml` is updated with a hashed password.

### Removing a User (Work in progress)

- Run this command with the name of user
  - `docker exec -it hypertrophy-mysql mysql -p -e "delete from fitness.users where name = '{name}'"`
- Delete the user from `config.yml`

## Scoring

There is a user setting called Scoring. After the last set of each muscle group,
it asks how pumped the muscle got, how sore it got from the last workout,
and how much effort it took.

Based on the feedback, it will either add a set to next week's exercise or
keep it the same.
