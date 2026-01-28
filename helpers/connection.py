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
