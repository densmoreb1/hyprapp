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

    def execute_query(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                return self.cursor.fetchall()
            else:
                self.connection.commit()
        except connector.Error as e:
            return f"Error executing query: {e}"

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
                    %s,        -- meso_id
                    %s,        -- name
                    %s,        -- user_id
                    %s,        -- completed
                    %s,        -- completed_day
                    %s,        -- set_id
                    %s,        -- reps
                    %s,        -- weight
                    %s,        -- order_id
                    %s,        -- exercise_id
                    %s,        -- day_id
                    %s,        -- week_id
                    NOW()      -- date_created (current timestamp)
                )
                """
        self.connection.cursor().execute(
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
