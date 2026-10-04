"""Auth routes — session rides an httpOnly cookie, never JSON tokens."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response

from lib.permissions import require
from lib.auth import (
    COOKIE_NAME,
    create_session,
    current_user,
    destroy_session,
    hash_password,
    verify_password,
)
from lib.db import db
from models.schemas import LoginInput, PasswordChange, RegisterInput, User

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


@router.post("/register", response_model=User)
async def register(payload: RegisterInput, admin: dict = Depends(require("kullanici:yonet"))):
    """Açık kayıt kapalı — hesaplar yalnızca yetkili kullanıcı tarafından açılır."""
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")
    user = User(email=email, ad_soyad=payload.ad_soyad, rol="izleyici")
    doc = user.model_dump()
    doc["sifre_hash"] = hash_password(payload.sifre)
    await db.users.insert_one(doc)
    return user


MAX_FAILED = 10
MAX_FAILED_EMAIL = 20
LOCK_WINDOW_MIN = 15


def _client_ip(request: Request) -> str:
    """Ters vekil arkasında gerçek istemci IP'si (ilk X-Forwarded-For girdisi)."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "-"


async def _failed_counts(email: str, key: str) -> tuple[int, int]:
    since = datetime.now(timezone.utc) - timedelta(minutes=LOCK_WINDOW_MIN)
    by_key = await db.login_attempts.count_documents({"key": key, "created_at": {"$gte": since}})
    by_email = await db.login_attempts.count_documents(
        {"email": email, "created_at": {"$gte": since}}
    )
    return by_key, by_email


@router.post("/login", response_model=User)
async def login(payload: LoginInput, request: Request, response: Response):
    email = payload.email.lower().strip()
    key = f"{email}|{_client_ip(request)}"
    by_key, by_email = await _failed_counts(email, key)
    if by_key >= MAX_FAILED or by_email >= MAX_FAILED_EMAIL:
        raise HTTPException(
            status_code=429,
            detail=f"Çok fazla hatalı giriş denemesi — {LOCK_WINDOW_MIN} dakika sonra tekrar deneyin",
        )
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.sifre, user.get("sifre_hash", "")):
        await db.login_attempts.insert_one(
            {"key": key, "email": email, "created_at": datetime.now(timezone.utc)}
        )
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    await db.login_attempts.delete_many({"email": email})
    _set_cookie(response, await create_session(user["id"]))
    return User(**user)


@router.post("/logout")
async def logout(response: Response, pergola_session: str | None = Cookie(default=None)):
    await destroy_session(pergola_session)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=User)
async def me(user: dict = Depends(current_user)):
    return User(**user)


@router.put("/sifre", response_model=User)
async def change_own_password(payload: PasswordChange, user: dict = Depends(current_user)):
    """Kullanıcı kendi şifresini değiştirir; diğer tüm oturumları kapatır."""
    if not verify_password(payload.mevcut_sifre, user.get("sifre_hash", "")):
        raise HTTPException(status_code=401, detail="Mevcut şifre hatalı")
    if payload.yeni_sifre == payload.mevcut_sifre:
        raise HTTPException(status_code=400, detail="Yeni şifre eskisiyle aynı olamaz")
    await db.users.update_one(
        {"id": user["id"]}, {"$set": {"sifre_hash": hash_password(payload.yeni_sifre)}}
    )
    await db.sessions.delete_many({"user_id": user["id"]})
    return User(**{k: v for k, v in user.items() if k != "sifre_hash"})
