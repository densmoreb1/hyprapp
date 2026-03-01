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
        self.connection = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.connection = connector.connect(**self.config)
            self.cursor = self.connection.cursor()
        except connector.Error as e:
            print("Error while connecting to MySQL", e)
            self.connection = None

    def execute_query(
        self,
        query: str,
        params: tuple,
    ) -> list:
        try:
            if self.cursor and query.strip().upper().startswith("SELECT"):
                self.cursor.execute(query, params=params)
                return self.cursor.fetchall()
            else:
                if self.connection:
                    self.connection.commit()
                return []
        except connector.Error as e:
            print(f"Error executing query: {e}")
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
