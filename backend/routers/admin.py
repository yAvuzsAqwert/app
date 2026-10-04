"""Kullanıcı & rol yönetimi + döviz kurları (elle girilen, TRY bazlı)."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from lib.auth import current_user, hash_password
from lib.db import db
from lib.permissions import (
    ALL_PERMISSIONS,
    DEFAULT_ROLE,
    PERMISSIONS,
    ROLE_DEFAULTS,
    permissions_of,
    require,
)
from models.schemas import (
    ExchangeRate,
    RoleCreate,
    RoleRename,
    RateInput,
    Role,
    RolePermissionUpdate,
    UserAccount,
    PasswordReset,
    UserCreate,
    UserRoleUpdate,
)

router = APIRouter(tags=["admin"])


def _aware(doc: dict) -> dict:
    for key in ("created_at", "guncellenme"):
        value = doc.get(key)
        if isinstance(value, datetime) and value.tzinfo is None:
            doc[key] = value.replace(tzinfo=timezone.utc)
    return doc


# ---------- yetki sözlüğü ----------
@router.get("/permissions")
async def permission_catalog(user: dict = Depends(current_user)) -> dict[str, str]:
    return PERMISSIONS


# ---------- roller ----------
@router.get("/roles", response_model=List[Role])
async def list_roles(user: dict = Depends(require("kullanici:yonet"))):
    rows = await db.roles.find().to_list(100)
    return [Role(**r) for r in rows]


@router.put("/roles/{kod}", response_model=Role)
async def update_role(
    kod: str, payload: RolePermissionUpdate, user: dict = Depends(require("kullanici:yonet"))
):
    role = await db.roles.find_one({"kod": kod})
    if not role:
        raise HTTPException(status_code=404, detail="Rol bulunamadı")
    if kod == "admin":
        raise HTTPException(status_code=409, detail="Admin rolü daima tüm yetkilere sahiptir")
    gecersiz = [y for y in payload.yetkiler if y not in ALL_PERMISSIONS]
    if gecersiz:
        raise HTTPException(status_code=400, detail=f"Geçersiz yetki: {gecersiz[0]}")
    await db.roles.update_one({"kod": kod}, {"$set": {"yetkiler": payload.yetkiler}})
    fresh = await db.roles.find_one({"kod": kod})
    return Role(**(fresh or {}))


@router.post("/roles", response_model=Role, status_code=201)
async def create_role(payload: RoleCreate, user: dict = Depends(require("kullanici:yonet"))):
    kod = payload.kod.strip().lower()
    label = payload.label.strip()
    if not kod or not label:
        raise HTTPException(status_code=400, detail="Rol kodu ve adı zorunlu")
    if not all(c.isalnum() or c in "-_" for c in kod):
        raise HTTPException(
            status_code=400, detail="Rol kodu yalnızca harf, rakam, - ve _ içerebilir"
        )
    if await db.roles.find_one({"kod": kod}):
        raise HTTPException(status_code=409, detail="Bu rol kodu zaten var")
    gecersiz = [y for y in payload.yetkiler if y not in ALL_PERMISSIONS]
    if gecersiz:
        raise HTTPException(status_code=400, detail=f"Geçersiz yetki: {gecersiz[0]}")
    doc = {"kod": kod, "label": label, "yetkiler": payload.yetkiler, "sistem": False}
    await db.roles.insert_one(dict(doc))
    return Role(**doc)


@router.put("/roles/{kod}/ad", response_model=Role)
async def rename_role(
    kod: str, payload: RoleRename, user: dict = Depends(require("kullanici:yonet"))
):
    role = await db.roles.find_one({"kod": kod})
    if not role:
        raise HTTPException(status_code=404, detail="Rol bulunamadı")
    label = payload.label.strip()
    if not label:
        raise HTTPException(status_code=400, detail="Rol adı zorunlu")
    await db.roles.update_one({"kod": kod}, {"$set": {"label": label}})
    fresh = await db.roles.find_one({"kod": kod})
    return Role(**(fresh or {}))


@router.delete("/roles/{kod}")
async def delete_role(kod: str, user: dict = Depends(require("kullanici:yonet"))):
    role = await db.roles.find_one({"kod": kod})
    if not role:
        raise HTTPException(status_code=404, detail="Rol bulunamadı")
    if kod == "admin" or role.get("sistem"):
        raise HTTPException(status_code=409, detail="Admin rolü silinemez")
    if kod in ROLE_DEFAULTS:
        raise HTTPException(status_code=409, detail="Hazır roller silinemez, yetkileri düzenlenir")
    kullanan = await db.users.count_documents({"rol": kod})
    if kullanan:
        raise HTTPException(
            status_code=409, detail=f"Bu rol {kullanan} kullanıcıda kullanılıyor, önce rolü değiştirin"
        )
    await db.roles.delete_one({"kod": kod})
    return {"ok": True}


# ---------- kullanıcılar ----------
@router.get("/users", response_model=List[UserAccount])
async def list_users(user: dict = Depends(require("kullanici:yonet"))):
    rows = await db.users.find().sort("created_at", 1).to_list(200)
    out: List[UserAccount] = []
    for r in rows:
        r = _aware(r)
        out.append(
            UserAccount(
                id=r["id"],
                email=r["email"],
                ad_soyad=r.get("ad_soyad", ""),
                rol=r.get("rol", DEFAULT_ROLE),
                created_at=r["created_at"],
            )
        )
    return out


@router.post("/users", response_model=UserAccount)
async def create_user(payload: UserCreate, user: dict = Depends(require("kullanici:yonet"))):
    email = payload.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")
    if not await db.roles.find_one({"kod": payload.rol}):
        raise HTTPException(status_code=400, detail="Geçersiz rol")
    if len(payload.sifre) < 6:
        raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalı")
    from models.schemas import User

    yeni = User(email=email, ad_soyad=payload.ad_soyad)
    doc = yeni.model_dump()
    doc["rol"] = payload.rol
    doc["sifre_hash"] = hash_password(payload.sifre)
    await db.users.insert_one(doc)
    return UserAccount(
        id=yeni.id, email=email, ad_soyad=yeni.ad_soyad, rol=payload.rol, created_at=yeni.created_at
    )


@router.put("/users/{user_id}/rol", response_model=UserAccount)
async def set_user_role(
    user_id: str, payload: UserRoleUpdate, user: dict = Depends(require("kullanici:yonet"))
):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    if not await db.roles.find_one({"kod": payload.rol}):
        raise HTTPException(status_code=400, detail="Geçersiz rol")
    # Son admin kendi yetkisini düşürüp sistemi kilitleyemez.
    if target.get("rol") == "admin" and payload.rol != "admin":
        kalan = await db.users.count_documents({"rol": "admin", "id": {"$ne": user_id}})
        if kalan == 0:
            raise HTTPException(status_code=409, detail="En az bir admin kalmalı")
    await db.users.update_one({"id": user_id}, {"$set": {"rol": payload.rol}})
    fresh = _aware(await db.users.find_one({"id": user_id}) or {})
    return UserAccount(
        id=fresh["id"],
        email=fresh["email"],
        ad_soyad=fresh.get("ad_soyad", ""),
        rol=fresh.get("rol", DEFAULT_ROLE),
        created_at=fresh["created_at"],
    )


@router.put("/users/{user_id}/sifre", response_model=UserAccount)
async def reset_user_password(
    user_id: str, payload: PasswordReset, user: dict = Depends(require("kullanici:yonet"))
):
    """Yönetici bir kullanıcının şifresini sıfırlar; o kullanıcının oturumları kapatılır."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    await db.users.update_one(
        {"id": user_id}, {"$set": {"sifre_hash": hash_password(payload.yeni_sifre)}}
    )
    await db.sessions.delete_many({"user_id": user_id})
    target = _aware(await db.users.find_one({"id": user_id}) or {})
    return UserAccount(
        id=target["id"],
        email=target["email"],
        ad_soyad=target.get("ad_soyad", ""),
        rol=target.get("rol", DEFAULT_ROLE),
        created_at=target["created_at"],
    )


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require("kullanici:yonet"))):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    if target["id"] == user["id"]:
        raise HTTPException(status_code=409, detail="Kendi hesabınızı silemezsiniz")
    if target.get("rol") == "admin":
        kalan = await db.users.count_documents({"rol": "admin", "id": {"$ne": user_id}})
        if kalan == 0:
            raise HTTPException(status_code=409, detail="En az bir admin kalmalı")
    await db.users.delete_one({"id": user_id})
    await db.sessions.delete_many({"user_id": user_id})
    return {"ok": True}


@router.get("/my-permissions")
async def my_permissions(user: dict = Depends(current_user)) -> dict:
    rol = user.get("rol", DEFAULT_ROLE)
    role = await db.roles.find_one({"kod": rol})
    return {
        "rol": rol,
        "rol_label": (role or {}).get("label", rol),
        "yetkiler": await permissions_of(rol),
    }


# ---------- döviz kurları (TRY bazlı, elle girilir) ----------
@router.get("/kurlar", response_model=List[ExchangeRate])
async def list_rates(user: dict = Depends(current_user)):
    rows = await db.rates.find().sort("para_birimi", 1).to_list(50)
    return [ExchangeRate(**_aware(r)) for r in rows]


@router.put("/kurlar", response_model=List[ExchangeRate])
async def save_rates(payload: RateInput, user: dict = Depends(require("kur:yonet"))):
    for row in payload.kurlar:
        if row.kur <= 0:
            raise HTTPException(status_code=400, detail="Kur sıfırdan büyük olmalı")
        await db.rates.update_one(
            {"para_birimi": row.para_birimi.upper()},
            {
                "$set": {
                    "para_birimi": row.para_birimi.upper(),
                    "kur": row.kur,
                    "guncellenme": datetime.now(timezone.utc),
                    "guncelleyen": user.get("ad_soyad", ""),
                }
            },
            upsert=True,
        )
    rows = await db.rates.find().sort("para_birimi", 1).to_list(50)
    return [ExchangeRate(**_aware(r)) for r in rows]
