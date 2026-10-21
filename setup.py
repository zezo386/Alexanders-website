import os

import psycopg
from psycopg.rows import dict_row


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Add it in Vercel → Settings → Environment Variables, "
            "or export it locally before running."
        )
    return url


def get_conn():
    return psycopg.connect(
        _database_url(),
        row_factory=dict_row,
        connect_timeout=10,
        sslmode="require",
    )


def setup():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS users")
            cur.execute("DROP TABLE IF EXISTS pending_users")
            cur.execute("DROP TABLE IF EXISTS events")


            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username      TEXT NOT NULL UNIQUE,
                    id            TEXT NOT NULL PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role          TEXT NOT NULL DEFAULT 'user',
                    created_at    TIMESTAMPTZ DEFAULT NOW(),
                    national_id   TEXT NOT NULL,
                    college       TEXT NOT NULL,
                    full_name     TEXT NOT NULL,
                    whatsapp_number TEXT NOT NULL,
                    academic_year INTEGER NOT NULL,
                    department TEXT NOT NULL DEFAULT 'OC',
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pending_users (
                    username      TEXT NOT NULL UNIQUE,
                    id            TEXT NOT NULL PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    requested_at  TIMESTAMPTZ DEFAULT NOW(),
                    interview_at  TIMESTAMPTZ,
                    status        TEXT NOT NULL DEFAULT 'pending',
                    national_id   TEXT NOT NULL,
                    college       TEXT NOT NULL,
                    full_name     TEXT NOT NULL,
                    whatsapp_number TEXT NOT NULL,
                    academic_year INTEGER NOT NULL,
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    name TEXT NOT NULL,
                    id   SERIAL PRIMARY KEY,
                    date TIMESTAMPTZ DEFAULT NOW(),
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    user_id     TEXT NOT NULL REFERENCES users(id),
                    event_id    INTEGER NOT NULL REFERENCES events(id),
                    attended_at TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (user_id, event_id)
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_attendance_event
                ON attendance (event_id)
            """)

        conn.commit()
    finally:
        conn.close()