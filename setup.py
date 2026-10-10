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
    """
    Open a fresh connection. Neon's pooler handles connection reuse,
    so we don't need our own pool object.
    """
    return psycopg.connect(
        _database_url(),
        row_factory=dict_row,
        connect_timeout=10,
        sslmode="require",  # Neon and most managed PG require SSL
    )


def setup():
    """
    Idempotent — safe to run on every cold start.
    Uses CREATE TABLE IF NOT EXISTS, so running repeatedly does nothing.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username      TEXT NOT NULL UNIQUE,
                    id            TEXT NOT NULL PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role          TEXT NOT NULL DEFAULT 'user',
                    created_at    TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pending_users (
                    username      TEXT NOT NULL UNIQUE,
                    id            TEXT NOT NULL PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    requested_at  TIMESTAMPTZ DEFAULT NOW(),
                    interview_at  TIMESTAMPTZ,
                    status        TEXT NOT NULL DEFAULT 'pending'
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    name TEXT NOT NULL,
                    id   SERIAL PRIMARY KEY
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

            # Index for the CSV export's join-heavy query
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_attendance_event
                ON attendance (event_id)
            """)

        conn.commit()
    finally:
        conn.close()