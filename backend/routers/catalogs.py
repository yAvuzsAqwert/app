"""Tanım listeleri CRUD — süreç aşaması, ürün, renk, kumaş, tedarikçi, para birimi…"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from lib.auth import current_user
from lib.permissions import require
from lib.catalog import CATALOG_TYPES, USAGE, list_catalog, slugify
from lib.db import db
from models.schemas import (
    CatalogBulkIds,
    CatalogBulkResult,
    CatalogBulkStatus,
    CatalogCreate,
    CatalogItem,
    CatalogReorder,
    CatalogUpdate,
)

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


async def _usage_count(tip: str, deger: str) -> int:
    total = 0
    for collection, field in USAGE.get(tip, []):
        total += await db[collection].count_documents({field: deger})
    return total


async def _with_usage(rows: List[dict], tip: str) -> List[CatalogItem]:
    out: List[CatalogItem] = []
    for row in rows:
        item = CatalogItem(**row)
        item.kullanim = await _usage_count(tip, item.deger)
        out.append(item)
    return out


@router.get("/types")
async def types(user: dict = Depends(current_user)) -> dict[str, str]:
    return CATALOG_TYPES


@router.get("/{tip}", response_model=List[CatalogItem])
async def get_catalog(tip: str, user: dict = Depends(current_user)):
    if tip not in CATALOG_TYPES:
        raise HTTPException(status_code=404, detail="Tanım tipi bulunamadı")
    rows = await list_catalog(tip, sadece_aktif=False)
    return await _with_usage(rows, tip)


@router.post("/{tip}", response_model=CatalogItem)
async def create_catalog(tip: str, payload: CatalogCreate, user: dict = Depends(require("tanim:yonet"))):
    if tip not in CATALOG_TYPES:
        raise HTTPException(status_code=404, detail="Tanım tipi bulunamadı")
    label = payload.label.strip()
    # Aşama ve fatura tipi anahtar üretir; diğer listelerde değer = etiket.
    deger = (payload.deger or "").strip() or (
        slugify(label) if tip in ("asama", "fatura_tipi") else label
    )
    if await db.catalogs.find_one({"tip": tip, "deger": deger}):
        raise HTTPException(status_code=409, detail="Bu tanım zaten mevcut")
    son = await db.catalogs.find({"tip": tip}).sort("sira", -1).to_list(1)
    item = CatalogItem(
        tip=tip, deger=deger, label=label, sira=(son[0]["sira"] + 1) if son else 0
    )
    await db.catalogs.insert_one(item.model_dump(exclude={"kullanim"}))
    return item


@router.put("/{tip}/{item_id}", response_model=CatalogItem)
async def update_catalog(
    tip: str, item_id: str, payload: CatalogUpdate, user: dict = Depends(require("tanim:yonet"))
):
    row = await db.catalogs.find_one({"id": item_id, "tip": tip})
    if not row:
        raise HTTPException(status_code=404, detail="Tanım bulunamadı")
    await db.catalogs.update_one(
        {"id": item_id}, {"$set": {"label": payload.label.strip(), "aktif": payload.aktif}}
    )
    fresh = await db.catalogs.find_one({"id": item_id})
    item = CatalogItem(**(fresh or {}))
    item.kullanim = await _usage_count(tip, item.deger)
    return item


@router.delete("/{tip}/{item_id}")
async def delete_catalog(tip: str, item_id: str, user: dict = Depends(require("tanim:yonet"))):
    row = await db.catalogs.find_one({"id": item_id, "tip": tip})
    if not row:
        raise HTTPException(status_code=404, detail="Tanım bulunamadı")
    kullanim = await _usage_count(tip, row["deger"])
    if kullanim:
        raise HTTPException(
            status_code=409,
            detail=f"Bu tanım {kullanim} kayıtta kullanılıyor, silinemez. Pasife alabilirsiniz.",
        )
    if tip == "asama" and await db.catalogs.count_documents({"tip": "asama"}) <= 2:
        raise HTTPException(status_code=409, detail="En az iki süreç aşaması kalmalı")
    await db.catalogs.delete_one({"id": item_id})
    return {"ok": True}


@router.post("/{tip}/bulk-delete", response_model=CatalogBulkResult)
async def bulk_delete_catalog(
    tip: str, payload: CatalogBulkIds, user: dict = Depends(require("tanim:yonet"))
):
    """Seçili tanımları siler; kullanımda olanlar atlanır ve gerekçesiyle döner."""
    if tip not in CATALOG_TYPES:
        raise HTTPException(status_code=404, detail="Tanım tipi bulunamadı")
    if not payload.ids:
        raise HTTPException(status_code=400, detail="Tanım seçilmedi")
    silinen = 0
    atlanan: List[str] = []
    for item_id in payload.ids:
        row = await db.catalogs.find_one({"id": item_id, "tip": tip})
        if not row:
            atlanan.append("Kayıt bulunamadı")
            continue
        if await _usage_count(tip, row["deger"]):
            atlanan.append(f"{row['label']}: kullanımda")
            continue
        if tip == "asama" and await db.catalogs.count_documents({"tip": "asama"}) <= 2:
            atlanan.append(f"{row['label']}: en az iki aşama kalmalı")
            continue
        await db.catalogs.delete_one({"id": item_id})
        silinen += 1
    return CatalogBulkResult(silinen=silinen, atlanan=atlanan)


@router.post("/{tip}/bulk-status", response_model=CatalogBulkResult)
async def bulk_status_catalog(
    tip: str, payload: CatalogBulkStatus, user: dict = Depends(require("tanim:yonet"))
):
    """Seçili tanımları topluca aktif / pasif yapar."""
    if tip not in CATALOG_TYPES:
        raise HTTPException(status_code=404, detail="Tanım tipi bulunamadı")
    if not payload.ids:
        raise HTTPException(status_code=400, detail="Tanım seçilmedi")
    res = await db.catalogs.update_many(
        {"id": {"$in": payload.ids}, "tip": tip}, {"$set": {"aktif": payload.aktif}}
    )
    return CatalogBulkResult(guncellenen=res.modified_count)


@router.patch("/{tip}/reorder", response_model=List[CatalogItem])
async def reorder_catalog(
    tip: str, payload: CatalogReorder, user: dict = Depends(require("tanim:yonet"))
):
    if tip not in CATALOG_TYPES:
        raise HTTPException(status_code=404, detail="Tanım tipi bulunamadı")
    for index, item_id in enumerate(payload.sirali_idler):
        await db.catalogs.update_one({"id": item_id, "tip": tip}, {"$set": {"sira": index}})
    rows = await list_catalog(tip, sadece_aktif=False)
    return await _with_usage(rows, tip)
