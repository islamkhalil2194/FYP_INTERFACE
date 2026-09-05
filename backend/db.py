import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Islam255#",
    "database": "smart_student_access"
}


def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            return connection

    except Error as e:
        print("Database connection error:", e)

    return None