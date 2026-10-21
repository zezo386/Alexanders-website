"""
Seed the database with a default admin, sample users, and events.

Usage:
    export DATABASE_URL="postgresql://...neon.tech/...?sslmode=require"
    python seed.py
"""

import uuid

from auth import hash_password
from setup import get_conn


# ---- edit these ----
SEED_USERS = [
    # (username, password, role)
    ("admin",   "admin123", "admin"),
    ("ahmed mohamed",   "pass1234", "user"),
    ("youssef ashraf",     "pass1234", "user"),
    ("mostafa elhalawany", "pass1234", "user"),
    ("ammar",   "pass1234", "user"),
    ("manar ayman",     "pass1234", "user"),
    ("ziad elhusiny",   "pass1234", "user"),
]

SEED_EVENTS = [
    "Orientation Day",
    "Tech Talk: FastAPI",
    "Hackathon 2026",
]

SEED_PENDING = [
    # (username, password) — appear in the admin pending list
    ("newbie1", "pass1234"),
    ("newbie2", "pass1234"),
]
# --------------------


def seed_users(cur):
    for username, password, role in SEED_USERS:
        cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        if cur.fetchone() is not None:
            print(f"  · user '{username}' already exists, skipping")
            continue

        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (username, id, password_hash, role) "
            "VALUES (%s, %s, %s, %s)",
            (username, user_id, hash_password(password), role),
        )
        print(f"  + {role:5s} '{username}' -> {user_id}  (password: {password})")


def seed_events(cur):
    for name in SEED_EVENTS:
        cur.execute("SELECT 1 FROM events WHERE name = %s", (name,))
        if cur.fetchone() is not None:
            print(f"  · event '{name}' already exists, skipping")
            continue

        cur.execute(
            "INSERT INTO events (name) VALUES (%s) RETURNING id",
            (name,),
        )
        event_id = cur.fetchone()["id"]
        print(f"  + event '{name}' -> #{event_id}")


def seed_pending(cur):
    for username, password in SEED_PENDING:
        cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        if cur.fetchone() is not None:
            print(f"  · user '{username}' already approved, skipping")
            continue

        cur.execute("SELECT 1 FROM pending_users WHERE username = %s", (username,))
        if cur.fetchone() is not None:
            print(f"  · pending '{username}' already exists, skipping")
            continue

        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO pending_users (username, id, password_hash) "
            "VALUES (%s, %s, %s)",
            (username, user_id, hash_password(password)),
        )
        print(f"  + pending '{username}' -> {user_id}")


def main():
    conn = get_conn()
    try:
        cur = conn.cursor()

        print("Seeding users...")
        seed_users(cur)

        print("\nSeeding events...")
        seed_events(cur)

        print("\nSeeding pending sign-ups...")
        seed_pending(cur)

        conn.commit()
        print("\nDone.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()