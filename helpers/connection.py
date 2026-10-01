from helpers import settings
import contextlib
import json
import pathlib
import pendulum
import sqlite3
import streamlit as st
import threading

APP_TZ = "UTC"


@st.cache_resource
def get_db():
    return Database()


def now_str() -> str:
    """
    Current time in the storage format described in schema.sql.
    Inputs:
        None
    Outputs:
        Timestamp text, 'YYYY-MM-DD HH:MM:SS'
    """
    return pendulum.now(APP_TZ).to_datetime_string()


def months_ago(months) -> str:
    """
    Date cutoff for filtering timestamps, on the same midnight basis as MySQL CURDATE().
    Inputs:
        months: how many months back to go
    Outputs:
        Date text, 'YYYY-MM-DD'
    """
    return pendulum.now(APP_TZ).subtract(months=months).to_date_string()


def fmt_date(value) -> str:
    """
    Format a stored timestamp for display; SQLite returns them as text.
    Inputs:
        value: timestamp text as stored, or None
    Outputs:
        Date as MM/DD/YYYY, or "" when there is no value
    """
    if not value:
        return ""
    return pendulum.parse(value).format("MM/DD/YYYY")


class Database:
    def __init__(self):
        self.path = settings.db_path()
        self.lock = threading.Lock()
        self.connect()
        self.bootstrap()

    def connect(self):
        # Sessions share one cached connection on separate threads; self.lock guards it.
        self.connection = sqlite3.connect(str(self.path), check_same_thread=False)

        self.connection.execute("PRAGMA journal_mode = WAL")
        # Off by default, so the meso_drafts cascade needs it set per connection.
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        # Under WAL this drops the per-commit fsync; a power cut loses recent commits.
        self.connection.execute("PRAGMA synchronous = NORMAL")

    def bootstrap(self):
        """
        Apply the schema, seeding only an empty database so renames are not undone.
        Inputs:
            None
        Outputs:
            None
        """
        here = pathlib.Path(__file__).parent

        # No lock: nothing shares the connection yet.
        self.connection.executescript((here / "schema.sql").read_text())
        row_count = self.connection.execute("""
            SELECT (SELECT COUNT(*) FROM users) + (SELECT COUNT(*) FROM exercises)
            """).fetchone()[0]
        if row_count == 0:
            self.connection.executescript((here / "seed.sql").read_text())

    def execute_query(
        self,
        query: str,
        params: tuple | None = None,
    ) -> list:
        """
        Run one statement against the shared connection.
        Inputs:
            query: SQL using ? placeholders
            params: values to bind, or None
        Outputs:
            Rows for a SELECT, otherwise an empty list
        """
        # One critical section: every session shares this connection.
        with self.lock:
            cursor = self.connection.cursor()
            try:
                cursor.execute(query, params if params else ())
                if query.strip().upper().startswith("SELECT"):
                    return cursor.fetchall()
                self.connection.commit()
                return []
            finally:
                cursor.close()

    @contextlib.contextmanager
    def transaction(self):
        """
        Run several statements as one unit, committing once at the end.
        Inputs:
            None
        Outputs:
            Cursor to run the statements on; execute_query would deadlock here
        """
        with self.lock:
            cursor = self.connection.cursor()
            try:
                yield cursor
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
            finally:
                cursor.close()

    def insert_set(
        self,
        meso_id,
        meso_name,
        user_id,
        completed,
        completed_day,
        set_id,
        reps,
        weight,
        order_id,
        exercise_id,
        day_id,
        week_id,
    ):
        query = """
                INSERT INTO mesos
                (
                    meso_id,
                    name,
                    user_id,
                    completed,
                    completed_day,
                    set_id,
                    reps,
                    weight,
                    order_id,
                    exercise_id,
                    day_id,
                    week_id,
                    date_created
                )
                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """

        self.execute_query(
            query,
            (
                meso_id,
                meso_name,
                user_id,
                completed,
                completed_day,
                set_id,
                reps,
                weight,
                order_id,
                exercise_id,
                day_id,
                week_id,
                now_str(),
            ),
        )

    def get_user_settings(self, name):
        sql = self.execute_query(
            """
            SELECT id
                , name
                , keep_score
                , past_mesos
                , months
            FROM users
            WHERE name = ?
            """,
            (name,),
        )
        return sql[0]

    def get_muscle_groups(self):
        sql = self.execute_query("""
            SELECT DISTINCT muscle_group
            FROM exercises
            ORDER BY muscle_group
            """)
        return [row[0] for row in sql]

    def get_exercises_by_group(self, muscle_group):
        sql = self.execute_query(
            """
            SELECT name
            FROM exercises
            WHERE muscle_group = ?
            ORDER BY name
            """,
            (muscle_group,),
        )
        return [row[0] for row in sql]

    def get_exercise_id(self, name):
        sql = self.execute_query(
            """
            SELECT id
            FROM exercises
            WHERE name = ?
            """,
            (name,),
        )
        return sql[0][0] if sql else None

    def get_muscle_group_by_exercise_id(self, exercise_id):
        sql = self.execute_query(
            """
            SELECT muscle_group
            FROM exercises
            WHERE id = ?
            """,
            (exercise_id,),
        )
        return sql[0][0] if sql else None

    def get_meso_id(self, name, user_id):
        sql = self.execute_query(
            """
            SELECT meso_id
            FROM mesos
            WHERE name = ?
                AND user_id = ?
            """,
            (name, user_id),
        )
        return sql[0][0] if sql else None

    def get_meso_names(self, user_id):
        sql = self.execute_query(
            """
            SELECT DISTINCT name
                , meso_id
            FROM mesos
            WHERE user_id = ?
            ORDER BY meso_id DESC
            """,
            (user_id,),
        )
        return [row[0] for row in sql]

    def get_meso_loadout(self, user_id, meso_id):
        sql = self.execute_query(
            """
            SELECT day_id
                , order_id
                , e.muscle_group
                , e.name
            FROM mesos m
            INNER JOIN exercises e ON m.exercise_id = e.id
            WHERE meso_id = ?
                AND user_id = ?
                AND week_id = (
                    SELECT MAX(week_id) - 1
                    FROM mesos
                    WHERE meso_id = ?
                        AND user_id = ?
                )
            GROUP BY day_id
                , order_id
                , e.muscle_group
                , e.name
            ORDER BY day_id
                , order_id
            """,
            (meso_id, user_id, meso_id, user_id),
        )
        loadout = []
        for day_id, _order_id, group, name in sql:
            while len(loadout) <= day_id:
                loadout.append([])
            loadout[day_id].append({"group": group, "exercise": name})
        return loadout

    def get_meso_draft(self, user_id):
        sql = self.execute_query(
            """
            SELECT draft
            FROM meso_drafts
            WHERE user_id = ?
            """,
            (user_id,),
        )
        if not sql or sql[0][0] is None:
            return None
        return json.loads(sql[0][0])

    def save_meso_draft(self, user_id, draft):
        self.execute_query(
            """
            INSERT INTO meso_drafts (user_id, draft, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                draft = excluded.draft
                , updated_at = excluded.updated_at
            """,
            (user_id, json.dumps(draft), now_str()),
        )

    def delete_meso_draft(self, user_id):
        self.execute_query(
            """
            DELETE
            FROM meso_drafts
            WHERE user_id = ?
            """,
            (user_id,),
        )
