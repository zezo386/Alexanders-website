from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import decode_token
from setup import get_conn

bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """
    Validate the bearer token, then re-fetch the user from the DB so
    that role changes and deletions take effect immediately (rather
    than waiting for the JWT to expire).
    """
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )

    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    try:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, role FROM users WHERE id = %s",
                    (payload["sub"],),
                )
                row = cur.fetchone()
        finally:
            conn.close()
    except Exception as e:
        # Print so the real error appears in Vercel's Runtime Logs.
        print(f"DB error in current_user: {e!r}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error during authentication",
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    return {
        "sub":      row["id"],
        "username": row["username"],
        "role":     row["role"],
    }


def admin_user(user: dict = Depends(current_user)) -> dict:
    """Reject the request unless the authenticated user has the admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user