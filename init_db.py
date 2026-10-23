"""Creates the SkillSwap database and tables by running database.sql.

Run:  python init_db.py
It is safe to run again. Existing data is not deleted.
"""
import os
import sys

import mysql.connector
from mysql.connector import errors as db_errors

from config import Config


def main():
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.sql")
    with open(sql_path, encoding="utf-8") as sql_file:
        lines = [line for line in sql_file if not line.strip().startswith("--")]
    statements = [part.strip() for part in "".join(lines).split(";") if part.strip()]

    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST, port=Config.DB_PORT,
            user=Config.DB_USER, password=Config.DB_PASSWORD,
            connection_timeout=5,
        )
    except db_errors.Error as error:
        print("Could not connect to MySQL.")
        print("Check that MySQL is running and that DB_USER and DB_PASSWORD in .env are correct.")
        print("Details:", error)
        sys.exit(1)

    cursor = conn.cursor()
    try:
        for statement in statements:
            cursor.execute(statement)
        conn.commit()
    except db_errors.Error as error:
        print("A SQL statement failed:", error)
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
    print("Done. The 'skillswap' database and all tables are ready.")


if __name__ == "__main__":
    main()
