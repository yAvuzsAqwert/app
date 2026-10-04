"""Auth routes — session rides an httpOnly cookie, never JSON tokens."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response

from lib.auth import (
    COOKIE_NAME,
    create_session,
    current_user,
    destroy_session,
    hash_password,
    verify_password,
)
from lib.db import db
from models.schemas import LoginInput, RegisterInput, User

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
        path="/",
    )


@router.post("/register", response_model=User)
async def register(payload: RegisterInput, response: Response):
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")
    user = User(email=email, ad_soyad=payload.ad_soyad, rol="izleyici")
    doc = user.model_dump()
    doc["sifre_hash"] = hash_password(payload.sifre)
    await db.users.insert_one(doc)
    _set_cookie(response, await create_session(user.id))
    return user


@router.post("/login", response_model=User)
async def login(payload: LoginInput, response: Response):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.sifre, user.get("sifre_hash", "")):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
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
