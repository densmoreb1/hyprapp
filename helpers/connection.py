from mysql import connector
import os


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
            self.cursor = self.connection.cursor()
        except connector.Error as e:
            print("Error while connecting to MySQL", e)
            raise

    def execute_query(
        self,
        query: str,
        params: tuple | None = None,
    ) -> list:
        self.cursor.execute(query, params if params else ())
        if query.strip().upper().startswith("SELECT"):
            return self.cursor.fetchall()
        else:
            self.connection.commit()
            return []

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
        return sql[0] if sql else None

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
