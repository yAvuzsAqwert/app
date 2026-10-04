"""İşlem günlüğü (audit log) + toplu proje işlemleri."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from lib.db import db
from lib.permissions import require
from models.schemas import Activity, BulkIds, BulkResult

router = APIRouter(tags=["audit"])

TIP_LABELS = {
    "olusturma": "Oluşturma",
    "asama": "Aşama değişimi",
    "guncelleme": "Güncelleme",
    "kalem": "Ürün kalemi",
    "muhasebe": "Muhasebe",
    "sandik": "Sandık",
    "evrak": "Evrak",
    "revizyon": "Revizyon",
    "silme": "Silme",
    "not": "Not",
}


def _aware(doc: dict) -> dict:
    value = doc.get("created_at")
    if isinstance(value, datetime) and value.tzinfo is None:
        doc["created_at"] = value.replace(tzinfo=timezone.utc)
    return doc


@router.get("/activities", response_model=List[Activity])
async def list_activities(
    kullanici: Optional[str] = Query(default=None),
    tip: Optional[str] = Query(default=None),
    baslangic: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    bitis: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=300, le=1000),
    user: dict = Depends(require("islem_log:goruntule")),
):
    query: dict = {}
    if kullanici:
        query["kullanici"] = kullanici
    if tip:
        query["tip"] = tip
    gun: dict = {}
    if baslangic:
        gun["$gte"] = baslangic
    if bitis:
        gun["$lte"] = bitis
    if gun:
        query["gun"] = gun
    rows = await db.activities.find(query).sort("created_at", -1).to_list(limit)
    return [Activity(**_aware(r)) for r in rows]


@router.get("/activities/kullanicilar", response_model=List[str])
async def activity_users(user: dict = Depends(require("islem_log:goruntule"))):
    names = await db.activities.distinct("kullanici")
    return sorted(n for n in names if n)


@router.post("/projects/bulk/archive", response_model=BulkResult)
async def bulk_archive(payload: BulkIds, user: dict = Depends(require("proje:sil"))):
    """Seçili projeleri arşivler (arsiv=True) — geri alınabilir."""
    if not payload.ids:
        raise HTTPException(status_code=400, detail="Proje seçilmedi")
    docs = await db.projects.find({"id": {"$in": payload.ids}}).to_list(500)
    for doc in docs:
        await db.projects.update_one({"id": doc["id"]}, {"$set": {"arsiv": payload.arsiv}}) 
        await db.activities.insert_one(
            Activity(
                proje_id=doc["id"],
                proje_kodu=doc.get("proje_kodu", ""),
                tip="guncelleme",
                mesaj="Toplu işlem: " + ("arşivlendi" if payload.arsiv else "arşivden çıkarıldı"),
                kullanici=user.get("ad_soyad", ""),
                gun=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ).model_dump()
        )
    return BulkResult(etkilenen=len(docs), bulunamayan=len(payload.ids) - len(docs))


@router.post("/projects/bulk/delete", response_model=BulkResult)
async def bulk_delete(payload: BulkIds, user: dict = Depends(require("proje:sil"))):
    """Seçili projeleri çöp kutusuna taşır — 30 gün içinde geri getirilebilir."""
    if not payload.ids:
        raise HTTPException(status_code=400, detail="Proje seçilmedi")
    from routers.trash import move_to_trash

    docs = await db.projects.find({"id": {"$in": payload.ids}}).to_list(500)
    for doc in docs:
        await move_to_trash(doc, user)
    return BulkResult(etkilenen=len(docs), bulunamayan=len(payload.ids) - len(docs))
