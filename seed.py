import hashlib
import secrets
import uuid

from setup import get_conn

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
    ).hex()
    return f"pbkdf2_sha256$200000${salt}${digest}"

USERS = [
    {
        "username": "alice",
        "password": "alice123",
        "role": "admin",
        "full_name": "Alice Hassan",
        "national_id": "12345678901234",
        "college": "Engineering",
        "whatsapp_number": "+201000000001",
        "academic_year": 3,
        "department": "OC",
    },
    {
        "username": "bob",
        "password": "bob123",
        "role": "user",
        "full_name": "Bob Ibrahim",
        "national_id": "12345678901235",
        "college": "Computer Science",
        "whatsapp_number": "+201000000002",
        "academic_year": 2,
        "department": "HR",
    },
    {
        "username": "carol",
        "password": "carol123",
        "role": "user",
        "full_name": "Carol Mahmoud",
        "national_id": "12345678901236",
        "college": "Medicine",
        "whatsapp_number": "+201000000003",
        "academic_year": 4,
        "department": "PR",
    },
    {
        "username": "dave",
        "password": "dave123",
        "role": "user",
        "full_name": "Dave Adel",
        "national_id": "12345678901237",
        "college": "Business",
        "whatsapp_number": "+201000000004",
        "academic_year": 1,
        "department": "OC",
    },
]


def seed():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for u in USERS:
                cur.execute(
                    """
                    INSERT INTO users (
                        username, id, password_hash, role,
                        national_id, college, full_name,
                        whatsapp_number, academic_year, department
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                    """,
                    (
                        u["username"],
                        str(uuid.uuid4()),
                        hash_password(u["password"]),
                        u["role"],
                        u["national_id"],
                        u["college"],
                        u["full_name"],
                        u["whatsapp_number"],
                        u["academic_year"],
                        u["department"],
                    ),
                )
        conn.commit()
        print(f"Seeded {len(USERS)} users (existing usernames were skipped).")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()