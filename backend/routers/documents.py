"""Proje evrakları — çizim, paketleme listesi, beyanname, fatura. GridFS'te saklanır (disk yok)."""

from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from lib.auth import current_user
from lib.permissions import require
from lib.dates import today_iso
from lib.db import db, get_db
from models.schemas import DOC_CATEGORIES, Activity, DocumentMeta

router = APIRouter(tags=["documents"])

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXT = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "gif",
    "heic",
    "xlsx",
    "xls",
    "csv",
    "docx",
    "doc",
    "dwg",
    "dxf",
    "txt",
}

def _bucket() -> AsyncIOMotorGridFSBucket:
    """Her istekte servis eden event loop içinde oluşturulur."""
    return AsyncIOMotorGridFSBucket(get_db(), bucket_name="evraklar")


def _safe_name(name: str) -> str:
    """Header değerini bozabilecek karakterleri temizler (ASCII-safe)."""
    cleaned = "".join(
        ch for ch in name.encode("ascii", "ignore").decode() if ch.isalnum() or ch in " .-_"
    ).strip()
    return cleaned or "evrak"


def _aware(doc: dict) -> dict:
    value = doc.get("created_at")
    if isinstance(value, datetime) and value.tzinfo is None:
        doc["created_at"] = value.replace(tzinfo=timezone.utc)
    return doc


async def _log(proje_id: str, proje_kodu: str, mesaj: str, user: dict) -> None:
    await db.activities.insert_one(
        Activity(
            proje_id=proje_id,
            proje_kodu=proje_kodu,
            tip="evrak",
            mesaj=mesaj,
            kullanici=user.get("ad_soyad", ""),
            gun=today_iso(),
        ).model_dump()
    )


@router.get("/projects/{proje_id}/evraklar", response_model=List[DocumentMeta])
async def list_documents(proje_id: str, user: dict = Depends(require("evrak:goruntule"))):
    docs = await db.documents.find({"proje_id": proje_id}).sort("created_at", -1).to_list(200)
    return [DocumentMeta(**_aware(d)) for d in docs]


@router.post("/projects/{proje_id}/evraklar", response_model=DocumentMeta)
async def upload_document(
    proje_id: str,
    file: UploadFile = File(...),
    kategori: str = Form(default="diger"),
    aciklama: str = Form(default=""),
    user: dict = Depends(require("evrak:yukle")),
):
    project = await db.projects.find_one({"id": proje_id})
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    if kategori not in DOC_CATEGORIES:
        raise HTTPException(status_code=400, detail="Geçersiz evrak kategorisi")

    name = file.filename or "evrak"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail="Desteklenmeyen dosya tipi. PDF, resim, Excel, Word ve çizim dosyaları yüklenebilir.",
        )

    payload = await file.read()
    if len(payload) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Dosya 10 MB sınırını aşıyor")
    if not payload:
        raise HTTPException(status_code=400, detail="Dosya boş")

    file_id = await _bucket().upload_from_stream(name, payload)
    meta = DocumentMeta(
        proje_id=proje_id,
        dosya_adi=name,
        kategori=kategori,
        boyut=len(payload),
        content_type=file.content_type or "application/octet-stream",
        aciklama=aciklama,
        yukleyen=user.get("ad_soyad", ""),
        file_id=str(file_id),
    )
    await db.documents.insert_one(meta.model_dump())
    await _log(
        proje_id,
        project.get("proje_kodu", ""),
        f"Evrak yüklendi: {name} ({DOC_CATEGORIES[kategori]})",
        user,
    )
    return meta


@router.get("/evraklar/{doc_id}/indir")
async def download_document(doc_id: str, user: dict = Depends(require("evrak:goruntule"))):
    meta = await db.documents.find_one({"id": doc_id})
    if not meta:
        raise HTTPException(status_code=404, detail="Evrak bulunamadı")
    try:
        stream = await _bucket().open_download_stream(ObjectId(meta["file_id"]))
    except Exception as exc:  # file row without its blob
        raise HTTPException(status_code=404, detail="Dosya içeriği bulunamadı") from exc
    data = await stream.read()
    return StreamingResponse(
        iter([data]),
        media_type=meta.get("content_type") or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(meta.get("dosya_adi", "evrak"))}"'},
    )


@router.get("/evraklar/{doc_id}/goruntule")
async def view_document(doc_id: str, user: dict = Depends(require("evrak:goruntule"))):
    """Tarayıcıda açılır (inline) — PDF ve resim evrakları buradan yazdırılabilir."""
    meta = await db.documents.find_one({"id": doc_id})
    if not meta:
        raise HTTPException(status_code=404, detail="Evrak bulunamadı")
    try:
        stream = await _bucket().open_download_stream(ObjectId(meta["file_id"]))
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Dosya içeriği bulunamadı") from exc
    data = await stream.read()
    return StreamingResponse(
        iter([data]),
        media_type=meta.get("content_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{_safe_name(meta.get("dosya_adi", "evrak"))}"'
        },
    )


@router.delete("/evraklar/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(require("evrak:sil"))):
    meta = await db.documents.find_one({"id": doc_id})
    if not meta:
        raise HTTPException(status_code=404, detail="Evrak bulunamadı")
    try:
        await _bucket().delete(ObjectId(meta["file_id"]))
    except Exception:  # blob already gone — still drop the row
        pass
    await db.documents.delete_one({"id": doc_id})
    project = await db.projects.find_one({"id": meta["proje_id"]})
    await _log(
        meta["proje_id"],
        (project or {}).get("proje_kodu", ""),
        f"Evrak silindi: {meta.get('dosya_adi', '')}",
        user,
    )
    return {"ok": True}


@router.get("/evrak-kategorileri")
async def categories() -> dict[str, str]:
    return DOC_CATEGORIES
