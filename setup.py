import sqlite3 as sq

DB_PATH = "database.db"


def get_conn():
    conn = sq.connect(DB_PATH)
    conn.row_factory = sq.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def setup():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS attendance")
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS pending_users")
    cursor.execute("DROP TABLE IF EXISTS events")

    cursor.execute("""
        CREATE TABLE users (
            username      TEXT NOT NULL UNIQUE,
            id            TEXT NOT NULL PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'user',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE pending_users (
            username      TEXT NOT NULL UNIQUE,
            id            TEXT NOT NULL PRIMARY KEY,
            password_hash TEXT NOT NULL,
            requested_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interview_at  TIMESTAMP,
            status        TEXT NOT NULL DEFAULT 'pending'
        )
    """)

    cursor.execute("""
        CREATE TABLE events (
            name TEXT NOT NULL,
            id   INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)

    cursor.execute("""
        CREATE TABLE attendance (
            user_id     TEXT NOT NULL,
            event_id    INTEGER NOT NULL,
            attended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, event_id),
            FOREIGN KEY (user_id)  REFERENCES users(id),
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    conn.commit()
    conn.close()