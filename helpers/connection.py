import mysql.connector
import os
from mysql.connector import Error


class MySQLDatabase:
    def __init__(self):
        self.config = {"user": "root", "password": os.environ["MYSQL_PASSWORD"], "host": "mysql", "database": "fitness"}
        self.connection = None
        self.cursor = None

        self.connect()

    def connect(self):
        """Establish a connection to the MySQL database."""
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                # print('Connected to MySQL database')
                self.cursor = self.connection.cursor()
        except Error as e:
            print("Error while connecting to MySQL", e)
            self.connection = None

    def execute_query(self, query, params=None):
        """Execute a single query."""
        if self.connection is None:
            raise Exception("Connection not established.")

        try:
            self.cursor.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                return self.cursor.fetchall()
            else:
                self.connection.commit()
                return self.cursor.rowcount
        except Error as e:
            return f"Error executing query: {e}"

    def close(self):
        """Close the cursor and connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection is closed")
