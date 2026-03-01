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
