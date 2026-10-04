"""Program adı + logo (marka ayarları). Logo GridFS'te saklanır, disk kullanılmaz.

Marka bilgisi giriş ekranında da gerektiği için okuma uçları oturum istemez;
yazma uçları `tanim:yonet` yetkisi ister.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from lib.db import db, get_db
from lib.permissions import require
from models.schemas import Branding, BrandingUpdate
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

router = APIRouter(tags=["branding"])

KEY = "branding"
MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_EXT = {"png", "jpg", "jpeg", "webp", "svg"}
def _bucket() -> AsyncIOMotorGridFSBucket:
    """Her istekte servis eden event loop içinde oluşturulur."""
    return AsyncIOMotorGridFSBucket(get_db(), bucket_name="branding")


async def _doc() -> dict:
    row = await db.settings.find_one({"key": KEY})
    return row or {}


def _model(row: dict) -> Branding:
    return Branding(
        program_adi=row.get("program_adi") or "PERGOLA TAKİP",
        alt_baslik=row.get("alt_baslik") or "Tente & Cam Sistemleri",
        logo_var=bool(row.get("logo_file_id")),
    )


@router.get("/branding", response_model=Branding)
async def get_branding():
    return _model(await _doc())


@router.put("/branding", response_model=Branding)
async def update_branding(payload: BrandingUpdate, user: dict = Depends(require("tanim:yonet"))):
    if not payload.program_adi.strip():
        raise HTTPException(status_code=400, detail="Program adı boş olamaz")
    await db.settings.update_one(
        {"key": KEY},
        {
            "$set": {
                "key": KEY,
                "program_adi": payload.program_adi.strip()[:40],
                "alt_baslik": payload.alt_baslik.strip()[:60],
            }
        },
        upsert=True,
    )
    return _model(await _doc())


@router.post("/branding/logo", response_model=Branding)
async def upload_logo(
    file: UploadFile = File(...), user: dict = Depends(require("tanim:yonet"))
):
    name = file.filename or "logo"
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in LOGO_EXT:
        raise HTTPException(status_code=400, detail="Logo PNG, JPG, WEBP veya SVG olmalı")
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Dosya boş")
    if len(payload) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=413, detail="Logo 2 MB sınırını aşıyor")

    row = await _doc()
    if row.get("logo_file_id"):
        try:
            await _bucket().delete(ObjectId(row["logo_file_id"]))
        except Exception:
            pass
    file_id = await _bucket().upload_from_stream(name, payload)
    await db.settings.update_one(
        {"key": KEY},
        {
            "$set": {
                "key": KEY,
                "logo_file_id": str(file_id),
                "logo_content_type": file.content_type
                or ("image/svg+xml" if ext == "svg" else f"image/{ext}"),
            }
        },
        upsert=True,
    )
    return _model(await _doc())


@router.delete("/branding/logo", response_model=Branding)
async def delete_logo(user: dict = Depends(require("tanim:yonet"))):
    row = await _doc()
    if row.get("logo_file_id"):
        try:
            await _bucket().delete(ObjectId(row["logo_file_id"]))
        except Exception:
            pass
    await db.settings.update_one(
        {"key": KEY}, {"$unset": {"logo_file_id": "", "logo_content_type": ""}}
    )
    return _model(await _doc())


@router.get("/branding/logo")
async def get_logo():
    row = await _doc()
    if not row.get("logo_file_id"):
        raise HTTPException(status_code=404, detail="Logo yüklenmemiş")
    try:
        stream = await _bucket().open_download_stream(ObjectId(row["logo_file_id"]))
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Logo bulunamadı") from exc
    data = await stream.read()
    return Response(
        content=data,
        media_type=row.get("logo_content_type") or "image/png",
        headers={"Cache-Control": "no-cache"},
    )
