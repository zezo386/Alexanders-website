import csv
import io
import uuid
import os
from contextlib import asynccontextmanager
from pathlib import Path

import qrcode
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from qrcode.constants import ERROR_CORRECT_H

from auth import create_token, hash_password, verify_password
from deps import admin_user, current_user
from setup import get_conn, setup

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs on cold start. Creates tables if they don't exist.
    # If the DB is unreachable, this raises and the function fails
    # with a clear error in Vercel's Runtime Logs.
    setup()
    yield


app = FastAPI(title="Attendance Scanner", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SignupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=4)
    national_id: str = Field(min_length=14,max_length=15)
    college: str
    academic_year: int
    full_name: str
    whatsapp_number: str = Field(min_length=11,max_length=13)
    department: str
    


class LoginRequest(BaseModel):
    username: str
    password: str


class EventRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    date: str # ISO-8601


class AttendRequest(BaseModel):
    user_id: str
    event_id: int


class ScheduleRequest(BaseModel):
    interview_at: str  # ISO-8601


class AdminCreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=4)
    role: str = "user"

@app.post("/signup")
def signup(req: SignupRequest):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE username = %s", (req.username,))
            if cur.fetchone() is not None:
                raise HTTPException(409, "Username already taken")
            cur.execute("SELECT 1 FROM pending_users WHERE username = %s", (req.username,))
            if cur.fetchone() is not None:
                raise HTTPException(409, "Username already taken")

            user_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO pending_users (username, id, password_hash, national_id, college, full_name, whatsapp_number, academic_year, department) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (req.username, user_id, hash_password(req.password), req.national_id, req.college, req.full_name, req.whatsapp_number, req.academic_year, req.department),
            )
        conn.commit()
    finally:
        conn.close()
    return {"status": "pending", "id": user_id}


@app.post("/login")
def login(req: LoginRequest):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash, role, department FROM users WHERE username = %s",
                (req.username,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(401, "Invalid username or password")

    token = create_token(
        user_id=row["id"], username=row["username"], role=row["role"], department=row["department"]
    )
    return {
        "access_token": token,
        "token_type":   "bearer",
        "expires_in":   24 * 3600,
        "user": {
            "id":       row["id"],
            "username": row["username"],
            "role":     row["role"],
            "department":row["department"]
        },
    }


@app.get("/me")
def me(user: dict = Depends(current_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT created_at FROM users WHERE id = %s",
                (user["sub"],),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return {
        "id":         user["sub"],
        "username":   user["username"],
        "role":       user["role"],
        "created_at": row["created_at"] if row else None,
    }

@app.get("/admin/pending")
def admin_list_pending(_admin: dict = Depends(admin_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *
                FROM pending_users
                WHERE status = 'pending'
                ORDER BY requested_at
            """)
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows


@app.post("/admin/pending/{pending_id}/schedule")
def admin_schedule(
    pending_id: str,
    req: ScheduleRequest,
    _admin: dict = Depends(admin_user),
):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pending_users WHERE id = %s AND status = 'pending'",
                (pending_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "Pending user not found")

            cur.execute(
                "UPDATE pending_users SET interview_at = %s WHERE id = %s",
                (req.interview_at, pending_id),
            )
        conn.commit()
    finally:
        conn.close()
    return {"status": "scheduled"}


@app.post("/admin/pending/{pending_id}/approve")
def admin_approve(pending_id: str, admin_approve: int = 0, _admin: dict = Depends(admin_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, password_hash, national_id, college, whatsapp_number, academic_year, full_name, department FROM pending_users "
                "WHERE id = %s AND status = 'pending'",
                (pending_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(404, "Pending user not found")

            cur.execute(
                "INSERT INTO users (username, id, password_hash, role, national_id, college, whatsapp_number, academic_year, full_name, department) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (row["username"], pending_id, row["password_hash"],"admin" if admin_approve else "user", row["national_id"], row["college"], row["wahtsapp_number"], row["academic_year"], row["full_name"], row["department"]),
            )
            cur.execute(
                "UPDATE pending_users SET status = 'approved' WHERE id = %s",
                (pending_id,),
            )
        conn.commit()
    finally:
        conn.close()
    return {"status": "approved"}


@app.post("/admin/pending/{pending_id}/reject")
def admin_reject(pending_id: str, _admin: dict = Depends(admin_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pending_users SET status = 'rejected' "
                "WHERE id = %s AND status = 'pending'",
                (pending_id,),
            )
        conn.commit()
    finally:
        conn.close()
    return {"status": "rejected"}

@app.get("/users")
def list_users(_admin: dict = Depends(admin_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users ORDER BY username"
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows

@app.get("/events")
def list_events():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM events ORDER BY id")
            rows = cur.fetchall()
    finally:
        conn.close()
    return rows


@app.post("/events")
def create_event(req: EventRequest, _admin: dict = Depends(admin_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO events (name, date) VALUES (%s, %s) RETURNING id",
                (req.name, req.date),
            )
            event_id = cur.fetchone()["id"]
        conn.commit()
    finally:
        conn.close()
    return {"name": req.name, "id": event_id, "date": req.date}

ROLE_COLORS = {
    "admin": "#4f9cf9",
    "user":  "#059669",
}

@app.get("/qrcode/{user_id}")
def get_qrcode(user_id: str, user: dict = Depends(current_user)):
    if user["role"] != "admin" and user["sub"] != user_id:
        raise HTTPException(403, "You can only view your own QR code")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(404, "User not found")

    fill = ROLE_COLORS.get(row["role"], "#0f1729")

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(user_id)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill, back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )

@app.post("/attend")
def attend(req: AttendRequest, _admin: dict = Depends(admin_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE id = %s", (req.user_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, "User not found")
            cur.execute("SELECT 1 FROM events WHERE id = %s", (req.event_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, "Event not found")

            cur.execute(
                "INSERT INTO attendance (user_id, event_id) VALUES (%s, %s) "
                "ON CONFLICT (user_id, event_id) DO NOTHING",
                (req.user_id, req.event_id),
            )
        conn.commit()
    finally:
        conn.close()
    return {"status": "attended", "user_id": req.user_id, "event_id": req.event_id}
@app.get("/export_users")
def export_users(_admin: dict = Depends(admin_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT full_name,
                       role,
                       department,
                       college,
                       academic_year,
                       national_id,
                       whatsapp_number
                FROM users
                ORDER BY username
            """)
            users = cur.fetchall()
    finally:
        conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)

    header = [
        "full name",
        "role",
        "department",
        "college",
        "academic year",
        "national_id",
        "whatsapp number",
    ]
    writer.writerow(header)

    for user in users:
        writer.writerow([
            user["full_name"],
            user["role"],
            user["department"],
            user["college"],
            user["academic_year"],
            user["national_id"],
            user["whatsapp_number"],
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )
@app.get("/export_attendance")
def export_csv(_admin: dict = Depends(admin_user)):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username FROM users ORDER BY username")
            users = cur.fetchall()

            cur.execute("SELECT id, name FROM events ORDER BY id")
            events = cur.fetchall()

            cur.execute("SELECT user_id, event_id FROM attendance")
            attended = {(r["user_id"], r["event_id"]) for r in cur.fetchall()}
    finally:
        conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)

    header = ["username", "id"] + [f"{name} (#{eid})" for eid, name in events]
    writer.writerow(header)

    for user_id, username in users:
        row = [username, user_id]
        for event_id, _ in events:
            row.append("x" if (user_id, event_id) in attended else "")
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance.csv"},
    )

BASE_DIR = Path(__file__).parent
WEB_DIR = "frontend"

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def root():
    return FileResponse(f"{WEB_DIR}/index.html")