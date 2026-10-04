"""Proforma revizyon geçmişi — her versiyon kalem + tutar anlık görüntüsü saklar."""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from lib.auth import current_user
from lib.dates import today_iso
from lib.db import db
from models.schemas import Activity, ProformaVersion, RevisionInput

router = APIRouter(tags=["revisions"])

SNAPSHOT_FIELDS = (
    "urun",
    "adet",
    "genislik_mm",
    "acilim_mm",
    "yapi_rengi",
    "panel_rengi",
    "aydinlatma",
    "cam_kombinasyonu",
    "cam_rengi",
    "zip_kumasi",
    "pergola_kumasi",
    "tedarikci",
    "birim_fiyat",
)


def _aware(doc: dict) -> dict:
    value = doc.get("created_at")
    if isinstance(value, datetime) and value.tzinfo is None:
        doc["created_at"] = value.replace(tzinfo=timezone.utc)
    return doc


async def snapshot(proje_id: str, kaynak: str, aciklama: str, user: dict) -> ProformaVersion:
    """Projenin o anki proforma halini yeni bir versiyon olarak kaydeder."""
    project = await db.projects.find_one({"id": proje_id})
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    items = await db.project_items.find({"proje_id": proje_id}).sort("created_at", 1).to_list(500)
    son = await db.proforma_versions.find({"proje_id": proje_id}).sort("versiyon", -1).to_list(1)
    m = project.get("muhasebe", {}) or {}
    satis = float(m.get("satis") or 0)
    iskonto = float(m.get("iskonto_tutari") or 0)
    transfer = float(m.get("transfer_ucreti") or 0)

    version = ProformaVersion(
        proje_id=proje_id,
        proje_kodu=project.get("proje_kodu", ""),
        versiyon=(son[0]["versiyon"] + 1) if son else 1,
        kaynak=kaynak,
        aciklama=aciklama,
        olusturan=user.get("ad_soyad", ""),
        durum=project.get("durum", ""),
        para_birimi=project.get("para_birimi", ""),
        satis=satis,
        iskonto_tutari=iskonto,
        transfer_ucreti=transfer,
        toplam=round(satis - iskonto + transfer, 2),
        kalem_sayisi=len(items),
        kalemler=[{k: i.get(k) for k in SNAPSHOT_FIELDS} for i in items],
    )
    await db.proforma_versions.insert_one(version.model_dump())
    await db.activities.insert_one(
        Activity(
            proje_id=proje_id,
            proje_kodu=version.proje_kodu,
            tip="revizyon",
            mesaj=f"Proforma Rev.{version.versiyon} kaydedildi"
            + (f" — {aciklama}" if aciklama else "")
            + (" (PDF indirildi)" if kaynak == "pdf" else ""),
            kullanici=user.get("ad_soyad", ""),
            gun=today_iso(),
        ).model_dump()
    )
    return version


@router.get("/projects/{proje_id}/revizyonlar", response_model=List[ProformaVersion])
async def list_revisions(proje_id: str, user: dict = Depends(current_user)):
    rows = (
        await db.proforma_versions.find({"proje_id": proje_id})
        .sort("versiyon", -1)
        .to_list(200)
    )
    return [ProformaVersion(**_aware(r)) for r in rows]


@router.post("/projects/{proje_id}/revizyonlar", response_model=ProformaVersion)
async def create_revision(
    proje_id: str, payload: RevisionInput, user: dict = Depends(current_user)
):
    return await snapshot(proje_id, "manuel", payload.aciklama.strip(), user)


@router.delete("/revizyonlar/{version_id}")
async def delete_revision(version_id: str, user: dict = Depends(current_user)):
    row = await db.proforma_versions.find_one({"id": version_id})
    if not row:
        raise HTTPException(status_code=404, detail="Revizyon bulunamadı")
    await db.proforma_versions.delete_one({"id": version_id})
    return {"ok": True}
