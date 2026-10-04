"""Çöp kutusu — silinen projeler 30 gün saklanır ve geri getirilebilir.

Proje silindiğinde proje, kalemleri, sandıkları, revizyonları ve işlem geçmişi tek bir
`trash` dokümanına taşınır. `silindi_at` üzerindeki TTL indeksi 30 gün sonra kaydı
otomatik siler (bkz. lib/db.py).
"""

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from lib.db import db
from lib.permissions import require
from models.schemas import Activity, TrashItem

router = APIRouter(tags=["trash"])

RETENTION_DAYS = 30


async def move_to_trash(project: dict, user: dict) -> None:
    """Projeyi ve bağlı kayıtlarını çöp kutusuna taşır (canlı koleksiyonlardan siler)."""
    proje_id = project["id"]
    snapshot = {
        "id": proje_id,
        "proje_kodu": project.get("proje_kodu", ""),
        "proje_adi": project.get("proje_adi", ""),
        "firma": project.get("firma", ""),
        "musteri": project.get("musteri", ""),
        "durum": project.get("durum", ""),
        "silindi_at": datetime.now(timezone.utc),
        "silen": user.get("ad_soyad", ""),
        "project": project,
        "kalemler": await db.project_items.find({"proje_id": proje_id}).to_list(1000),
        "sandiklar": await db.project_crates.find({"proje_id": proje_id}).to_list(500),
        "revizyonlar": await db.proforma_versions.find({"proje_id": proje_id}).to_list(200),
        "aktiviteler": await db.activities.find({"proje_id": proje_id}).to_list(1000),
    }
    for key in ("project", "kalemler", "sandiklar", "revizyonlar", "aktiviteler"):
        value = snapshot[key]
        if isinstance(value, list):
            for row in value:
                row.pop("_id", None)
        else:
            value.pop("_id", None)

    await db.trash.delete_many({"id": proje_id})
    await db.trash.insert_one(snapshot)
    await db.projects.delete_one({"id": proje_id})
    await db.project_items.delete_many({"proje_id": proje_id})
    await db.project_crates.delete_many({"proje_id": proje_id})
    await db.proforma_versions.delete_many({"proje_id": proje_id})
    await db.activities.delete_many({"proje_id": proje_id})
    await db.activities.insert_one(
        Activity(
            proje_id=proje_id,
            proje_kodu=project.get("proje_kodu", ""),
            tip="silme",
            mesaj=f"Proje çöp kutusuna taşındı ({RETENTION_DAYS} gün saklanacak): "
            f"{project.get('proje_adi', '')}",
            kullanici=user.get("ad_soyad", ""),
            gun=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        ).model_dump()
    )


def _item(row: dict) -> TrashItem:
    silindi = row.get("silindi_at")
    if isinstance(silindi, datetime) and silindi.tzinfo is None:
        silindi = silindi.replace(tzinfo=timezone.utc)
    kalan = RETENTION_DAYS - (datetime.now(timezone.utc) - silindi).days
    return TrashItem(
        id=row["id"],
        proje_kodu=row.get("proje_kodu", ""),
        proje_adi=row.get("proje_adi", ""),
        firma=row.get("firma", ""),
        musteri=row.get("musteri", ""),
        silindi_at=silindi,
        silen=row.get("silen", ""),
        kalan_gun=max(kalan, 0),
        kalem_adet=len(row.get("kalemler", [])),
        sandik_adet=len(row.get("sandiklar", [])),
    )


@router.get("/trash", response_model=List[TrashItem])
async def list_trash(user: dict = Depends(require("proje:sil"))):
    rows = await db.trash.find().sort("silindi_at", -1).to_list(500)
    return [_item(r) for r in rows]


@router.post("/trash/{proje_id}/restore", response_model=TrashItem)
async def restore(proje_id: str, user: dict = Depends(require("proje:sil"))):
    row = await db.trash.find_one({"id": proje_id})
    if not row:
        raise HTTPException(status_code=404, detail="Çöp kutusunda böyle bir proje yok")
    if await db.projects.find_one({"id": proje_id}):
        raise HTTPException(status_code=409, detail="Bu proje zaten aktif durumda")

    await db.projects.insert_one(row["project"])
    for coll, key in (
        ("project_items", "kalemler"),
        ("project_crates", "sandiklar"),
        ("proforma_versions", "revizyonlar"),
        ("activities", "aktiviteler"),
    ):
        rows = row.get(key) or []
        if rows:
            await db[coll].insert_many(rows)
    await db.trash.delete_one({"id": proje_id})
    await db.activities.insert_one(
        Activity(
            proje_id=proje_id,
            proje_kodu=row.get("proje_kodu", ""),
            tip="guncelleme",
            mesaj=f"Proje çöp kutusundan geri getirildi: {row.get('proje_adi', '')}",
            kullanici=user.get("ad_soyad", ""),
            gun=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        ).model_dump()
    )
    return _item(row)


@router.delete("/trash/{proje_id}")
async def purge(proje_id: str, user: dict = Depends(require("proje:sil"))):
    """Çöp kutusundaki kaydı kalıcı olarak yok eder."""
    row = await db.trash.find_one({"id": proje_id})
    if not row:
        raise HTTPException(status_code=404, detail="Çöp kutusunda böyle bir proje yok")
    await db.trash.delete_one({"id": proje_id})
    return {"ok": True}


@router.get("/trash/bilgi")
async def trash_info(user: dict = Depends(require("proje:sil"))) -> dict:
    adet = await db.trash.count_documents({})
    return {
        "adet": adet,
        "saklama_gun": RETENTION_DAYS,
        "en_eski_silinme": (
            (await db.trash.find().sort("silindi_at", 1).to_list(1)) or [{}]
        )[0].get("silindi_at"),
        "temizlenme_esigi": (
            datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        ).isoformat(),
    }
