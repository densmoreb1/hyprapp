# HyprApp

## Introduction

Python / Streamlit web app

- Tracks workouts
- Able to create custom programs
- Website that works on mobile and desktop

## Setup

### Quickstart

```sh
nix run github:densmoreb1/hyprapp
```

Website is available at `http://localhost:8501`

Login:

- username: test
- password: testing123

### Development

```sh
git clone https://github.com/densmoreb1/hyprapp.git
cd hyprapp
nix develop
streamlit run 01_Current_Workout.py
```

The dev shell also provides `sqlite3`, `black` and `sqlfluff`.

## Database

SQLite. Everything the app writes lives in one directory, set by
`HYPRAPP_STATE_DIR`:

| | State directory |
| --- | --- |
| `nix run` | `~/.local/share/hyprapp` |
| `nix develop` | `./state` |

Whatever launches the app creates that directory and sets the variable; the app
only reads it, and refuses to start if it is unset. It holds `fitness.db` and
`config.yml`. The schema in `helpers/schema.sql` is
applied on every start; `helpers/seed.sql` runs only when the database is empty,
so renamed exercises and deleted users stay that way. `config.yml` is seeded from
`.streamlit/config.yml.example` the first time it is needed.

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
  - `sqlite3 "${HYPRAPP_STATE_DIR:-$HOME/.local/share/hyprapp}/fitness.db" "pragma foreign_keys = on; delete from users where name = '{name}';"`
- Delete the user from `config.yml`

The `pragma` matters: without it SQLite skips the cascade and leaves the user's
saved program draft behind.

## Scoring

There is a user setting called Scoring. After the last set of each muscle group,
it asks how pumped the muscle got, how sore it got from the last workout,
and how much effort it took.

Based on the feedback, it will either add a set to next week's exercise or
keep it the same.
