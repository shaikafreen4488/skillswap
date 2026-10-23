"""Small helper functions for talking to MySQL.

Every function opens a connection, runs ONE query with parameters (%s),
and closes the cursor and the connection again. Parameters are never
glued into the SQL text, which protects against SQL injection.
"""
import mysql.connector
from config import Config


def get_connection():
    return mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        connection_timeout=5,
    )


def _run(sql, params, mode):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(sql, params)
        if mode == "all":
            return cursor.fetchall()
        if mode == "one":
            return cursor.fetchone()
        conn.commit()
        return cursor.lastrowid if mode == "insert" else cursor.rowcount
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def fetch_all(sql, params=()):
    """Return a list of rows (each row is a dictionary)."""
    return _run(sql, params, "all")


def fetch_one(sql, params=()):
    """Return one row (a dictionary) or None."""
    return _run(sql, params, "one")


def insert(sql, params=()):
    """Run an INSERT and return the new row id."""
    return _run(sql, params, "insert")


def execute(sql, params=()):
    """Run an UPDATE or DELETE and return the number of rows changed."""
    return _run(sql, params, "execute")
