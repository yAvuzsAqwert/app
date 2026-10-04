"""Bayi portalı — bayilere salt-okunur giriş: kendi projeleri, tahsilat ve bakiyesi.

Ekip oturumundan tamamen ayrı bir cookie (`bayi_session`) kullanır; portal tarafında
hiçbir yazma endpointi yoktur.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response

from lib.auth import current_user, hash_password, verify_password
from lib.catalog import stage_labels
from lib.db import db
from models.schemas import (
    DealerAccount,
    DealerAccountCreate,
    LoginInput,
    PortalProject,
    PortalSummary,
    Project,
)

router = APIRouter(tags=["portal"])

PORTAL_COOKIE = "bayi_session"


def _aware(doc: dict) -> dict:
    for key in ("created_at", "updated_at"):
        value = doc.get(key)
        if isinstance(value, datetime) and value.tzinfo is None:
            doc[key] = value.replace(tzinfo=timezone.utc)
    return doc


async def current_dealer(bayi_session: str | None = Cookie(default=None)) -> dict:
    """FastAPI dependency: portal cookie → bayi hesabı."""
    if not bayi_session:
        raise HTTPException(status_code=401, detail="Bayi oturumu bulunamadı")
    session = await db.dealer_sessions.find_one({"token": bayi_session})
    if not session:
        raise HTTPException(status_code=401, detail="Oturum geçersiz")
    account = await db.dealer_accounts.find_one({"id": session["account_id"]})
    if not account or not account.get("aktif", True):
        raise HTTPException(status_code=401, detail="Bayi hesabı pasif veya bulunamadı")
    return account


# ---------- ekip tarafı: portal hesabı yönetimi ----------
@router.get("/dealer-accounts", response_model=List[DealerAccount])
async def list_accounts(user: dict = Depends(current_user)):
    rows = await db.dealer_accounts.find().sort("created_at", -1).to_list(500)
    return [DealerAccount(**_aware(r)) for r in rows]


@router.post("/dealer-accounts", response_model=DealerAccount)
async def create_account(payload: DealerAccountCreate, user: dict = Depends(current_user)):
    email = payload.email.lower().strip()
    if not payload.firma.strip():
        raise HTTPException(status_code=400, detail="Firma adı zorunlu")
    if len(payload.sifre) < 6:
        raise HTTPException(status_code=400, detail="Şifre en az 6 karakter olmalı")
    if await db.dealer_accounts.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Bu e-posta ile bir portal hesabı mevcut")
    account = DealerAccount(
        email=email,
        firma=payload.firma.strip(),
        ulke=payload.ulke.strip(),
        yetkili=payload.yetkili.strip(),
    )
    doc = account.model_dump()
    doc["sifre_hash"] = hash_password(payload.sifre)
    await db.dealer_accounts.insert_one(doc)
    return account


@router.delete("/dealer-accounts/{account_id}")
async def delete_account(account_id: str, user: dict = Depends(current_user)):
    row = await db.dealer_accounts.find_one({"id": account_id})
    if not row:
        raise HTTPException(status_code=404, detail="Portal hesabı bulunamadı")
    await db.dealer_accounts.delete_one({"id": account_id})
    await db.dealer_sessions.delete_many({"account_id": account_id})
    return {"ok": True}


# ---------- bayi tarafı ----------
@router.post("/portal/login", response_model=DealerAccount)
async def portal_login(payload: LoginInput, response: Response):
    import secrets

    account = await db.dealer_accounts.find_one({"email": payload.email.lower().strip()})
    if not account or not verify_password(payload.sifre, account.get("sifre_hash", "")):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    if not account.get("aktif", True):
        raise HTTPException(status_code=403, detail="Bu bayi hesabı pasif")
    token = secrets.token_urlsafe(32)
    await db.dealer_sessions.insert_one(
        {"token": token, "account_id": account["id"], "created_at": datetime.now(timezone.utc)}
    )
    response.set_cookie(
        PORTAL_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 14,
        path="/",
    )
    return DealerAccount(**_aware(account))


@router.post("/portal/logout")
async def portal_logout(response: Response, bayi_session: str | None = Cookie(default=None)):
    if bayi_session:
        await db.dealer_sessions.delete_one({"token": bayi_session})
    response.delete_cookie(PORTAL_COOKIE, path="/")
    return {"ok": True}


@router.get("/portal/me", response_model=DealerAccount)
async def portal_me(account: dict = Depends(current_dealer)):
    return DealerAccount(**_aware(account))


@router.get("/portal/ozet", response_model=PortalSummary)
async def portal_summary(account: dict = Depends(current_dealer)):
    """Bayinin yalnızca kendi projeleri — salt okunur özet."""
    query: dict = {"firma": account["firma"]}
    if account.get("ulke"):
        query["ulke"] = account["ulke"]
    docs = await db.projects.find(query).to_list(1000)
    projects = [Project(**_aware(d)) for d in docs]
    labels = await stage_labels()

    rows = [
        PortalProject(
            proje_kodu=p.proje_kodu,
            proje_adi=p.proje_adi,
            musteri=p.musteri,
            durum=p.durum,
            durum_label=labels.get(p.durum, p.durum),
            proje_tarihi=p.proje_tarihi,
            termin_tarihi=p.termin_tarihi,
            sevk_tarihi=p.sevk_tarihi,
            para_birimi=p.para_birimi,
            toplam_satis=p.muhasebe.transfer_dahil_toplam_satis,
            tahsilat=p.muhasebe.toplam_tahsilat,
            bakiye=p.muhasebe.kalan_bakiye,
            odeme_durumu=p.muhasebe.odeme_durumu,
            arsiv=p.arsiv,
        )
        for p in sorted(projects, key=lambda x: x.proje_tarihi or "", reverse=True)
    ]
    currencies = {p.para_birimi for p in projects if p.para_birimi}
    return PortalSummary(
        firma=account["firma"],
        ulke=account.get("ulke", ""),
        yetkili=account.get("yetkili", ""),
        para_birimi=currencies.pop() if len(currencies) == 1 else "KARMA",
        proje_adet=len(rows),
        aktif_adet=len([r for r in rows if not r.arsiv]),
        toplam_satis=round(sum(r.toplam_satis for r in rows), 2),
        toplam_tahsilat=round(sum(r.tahsilat for r in rows), 2),
        acik_bakiye=round(sum(r.bakiye for r in rows), 2),
        projeler=rows,
    )
