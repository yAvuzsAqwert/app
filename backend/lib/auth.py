"""Cookie-session auth helpers. The session token lives in an httpOnly cookie only."""

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Cookie, HTTPException

from lib.db import db

COOKIE_NAME = "pergola_session"


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(hash_password(password, salt), stored)


async def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    await db.sessions.insert_one(
        {"token": token, "user_id": user_id, "created_at": datetime.now(timezone.utc)}
    )
    return token


async def destroy_session(token: str | None) -> None:
    if token:
        await db.sessions.delete_one({"token": token})


async def current_user(pergola_session: str | None = Cookie(default=None)) -> dict:
    """FastAPI dependency: resolves the session cookie to a user document."""
    if not pergola_session:
        raise HTTPException(status_code=401, detail="Oturum bulunamadı")
    session = await db.sessions.find_one({"token": pergola_session})
    if not session:
        raise HTTPException(status_code=401, detail="Oturum geçersiz")
    user = await db.users.find_one({"id": session["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")
    return user
