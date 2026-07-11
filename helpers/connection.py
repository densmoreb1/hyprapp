from mysql import connector
import json
import os
import streamlit as st


@st.cache_resource
def get_db():
    return MySQLDatabase()


class MySQLDatabase:
    def __init__(self):
        self.config = {
            "user": "root",
            "password": os.environ["MYSQL_PASSWORD"],
            "host": "mysql",
            "database": "fitness",
        }
        self.connect()

    def connect(self):
        try:
            self.connection = connector.connect(**self.config)
        except connector.Error as e:
            print("Error while connecting to MySQL", e)
            raise

    def execute_query(
        self,
        query: str,
        params: tuple | None = None,
    ) -> list:
        # The cached connection can go stale (MySQL wait_timeout); reconnect if so.
        self.connection.ping(reconnect=True, attempts=3, delay=1)
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params if params else ())
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            self.connection.commit()
            return []
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
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
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
            WHERE name = %s
            """,
            (name,),
        )
        return sql[0]

    def get_muscle_groups(self):
        sql = self.execute_query(
            """
            SELECT DISTINCT muscle_group
            FROM exercises
            ORDER BY muscle_group
            """
        )
        return [row[0] for row in sql]

    def get_exercises_by_group(self, muscle_group):
        sql = self.execute_query(
            """
            SELECT name
            FROM exercises
            WHERE muscle_group = %s
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
            WHERE name = %s
            """,
            (name,),
        )
        return sql[0][0] if sql else None

    def get_muscle_group_by_exercise_id(self, exercise_id):
        sql = self.execute_query(
            """
            SELECT muscle_group
            FROM exercises
            WHERE id = %s
            """,
            (exercise_id,),
        )
        return sql[0][0] if sql else None

    def get_meso_id(self, name, user_id):
        sql = self.execute_query(
            """
            SELECT meso_id
            FROM mesos
            WHERE name = %s
                AND user_id = %s
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
            WHERE user_id = %s
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
            WHERE meso_id = %s
                AND user_id = %s
                AND week_id = (
                    SELECT MAX(week_id) - 1
                    FROM mesos
                    WHERE meso_id = %s
                        AND user_id = %s
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
            WHERE user_id = %s
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
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                draft = %s
                , updated_at = NOW()
            """,
            (user_id, json.dumps(draft), json.dumps(draft)),
        )

    def delete_meso_draft(self, user_id):
        self.execute_query(
            """
            DELETE
            FROM meso_drafts
            WHERE user_id = %s
            """,
            (user_id,),
        )
