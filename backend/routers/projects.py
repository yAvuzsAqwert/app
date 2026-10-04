"""Project pipeline routes: projects, items (kalemler), crates (sandıklar), accounting, activity."""

from datetime import date, datetime, timezone
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from lib.auth import current_user
from lib.permissions import require, user_permissions
from lib.catalog import stage_keys, stage_labels
from lib.dates import today_iso
from lib.db import db
from models.schemas import (
    STAGE_LABELS,
    STAGES,
    Activity,
    CrateBase,
    DashboardStats,
    DeadlineAlert,
    ItemBase,
    Muhasebe,
    NoteInput,
    Project,
    ProjectCrate,
    ProjectCreate,
    ProjectDetail,
    ProjectItem,
    ProjectUpdate,
    StageCount,
    StageUpdate,
    compute_cbm,
    compute_muhasebe,
    now_utc,
)

router = APIRouter(tags=["projects"])


def _aware(doc: dict) -> dict:
    """Motor returns naive datetimes; normalise to aware UTC before Pydantic serialises."""
    for key in ("created_at", "updated_at"):
        value = doc.get(key)
        if isinstance(value, datetime) and value.tzinfo is None:
            doc[key] = value.replace(tzinfo=timezone.utc)
    return doc


async def _log(proje_id: str, proje_kodu: str, tip: str, mesaj: str, user: dict, **kw) -> Activity:
    act = Activity(
        proje_id=proje_id,
        proje_kodu=proje_kodu,
        tip=tip,
        mesaj=mesaj,
        kullanici=user.get("ad_soyad", ""),
        gun=today_iso(),
        **kw,
    )
    await db.activities.insert_one(act.model_dump())
    return act


async def _get_project(proje_id: str) -> dict:
    doc = await db.projects.find_one({"id": proje_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return _aware(doc)


async def _next_code() -> str:
    year = today_iso()[:4]
    count = await db.projects.count_documents({})
    while True:
        code = f"PRG-{year}-{count + 1:03d}"
        if not await db.projects.find_one({"proje_kodu": code}):
            return code
        count += 1


ALERT_WINDOW_DAYS = 7
# Stages past loading no longer need a production/dispatch warning.
ALERT_EXCLUDED_STAGES = {"yuklendi_sevk", "fatura", "gumruk_beyanname", "tamamlandi"}


def build_alerts(projects: List[Project]) -> List[DeadlineAlert]:
    """Termin ve sevk tarihlerine göre uyarılar — 'bugün' anchorı sunucudadır."""
    today = date.fromisoformat(today_iso())
    out: List[DeadlineAlert] = []
    for p in projects:
        if p.arsiv or p.durum in ALERT_EXCLUDED_STAGES:
            continue
        for tip, raw in (("termin", p.termin_tarihi), ("sevk", p.sevk_tarihi)):
            if not raw:
                continue
            try:
                when = date.fromisoformat(raw)
            except ValueError:
                continue
            kalan = (when - today).days
            if kalan < 0:
                seviye = "gecikti"
            elif kalan == 0:
                seviye = "bugun"
            elif kalan <= ALERT_WINDOW_DAYS:
                seviye = "yaklasiyor"
            else:
                continue
            out.append(
                DeadlineAlert(
                    proje_id=p.id,
                    proje_kodu=p.proje_kodu,
                    proje_adi=p.proje_adi,
                    musteri=p.musteri,
                    firma=p.firma,
                    durum=p.durum,
                    tip=tip,
                    tarih=raw,
                    kalan_gun=kalan,
                    seviye=seviye,
                )
            )
    return sorted(out, key=lambda a: a.kalan_gun)


async def _refresh_item_count(proje_id: str) -> None:
    count = await db.project_items.count_documents({"proje_id": proje_id})
    await db.projects.update_one(
        {"id": proje_id}, {"$set": {"kalem_sayisi": count, "updated_at": now_utc()}}
    )


async def _mask(project: Project, user: dict) -> Project:
    """muhasebe:goruntule yetkisi olmayan kullanıcıya finansal alanlar sıfırlanır."""
    if "muhasebe:goruntule" in await user_permissions(user):
        return project
    project.muhasebe = Muhasebe()
    return project


# ---------------- projects ----------------
@router.get("/projects", response_model=List[Project])
async def list_projects(
    durum: Optional[str] = Query(default=None),
    arsiv: Optional[bool] = Query(default=None),
    satis_tipi: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    user: dict = Depends(require("proje:goruntule")),
):
    query: dict = {}
    if durum:
        query["durum"] = durum
    if arsiv is not None:
        query["arsiv"] = arsiv
    if satis_tipi:
        query["satis_tipi"] = satis_tipi
    if q:
        q = re.escape(q[:80])
        query["$or"] = [
            {"proje_kodu": {"$regex": q, "$options": "i"}},
            {"proje_adi": {"$regex": q, "$options": "i"}},
            {"musteri": {"$regex": q, "$options": "i"}},
            {"firma": {"$regex": q, "$options": "i"}},
            {"ulke": {"$regex": q, "$options": "i"}},
            {"konteyner_no": {"$regex": q, "$options": "i"}},
        ]
    docs = await db.projects.find(query).sort("proje_tarihi", -1).to_list(500)
    gorunur = "muhasebe:goruntule" in await user_permissions(user)
    out = []
    for d in docs:
        p = Project(**_aware(d))
        p.muhasebe = compute_muhasebe(p.muhasebe)
        if not gorunur:
            p.muhasebe = Muhasebe()
        out.append(p)
    return out


@router.post("/projects", response_model=Project)
async def create_project(payload: ProjectCreate, user: dict = Depends(require("proje:ekle"))):
    if payload.durum not in await stage_keys():
        raise HTTPException(status_code=400, detail="Geçersiz aşama")
    data = payload.model_dump(exclude={"proje_kodu"})
    if not data.get("proje_tarihi"):
        data["proje_tarihi"] = today_iso()
    code = payload.proje_kodu or await _next_code()
    if await db.projects.find_one({"proje_kodu": code}):
        raise HTTPException(status_code=409, detail="Bu proje kodu zaten kullanılıyor")
    project = Project(proje_kodu=code, **data)
    project.muhasebe = compute_muhasebe(project.muhasebe)
    await db.projects.insert_one(project.model_dump())
    await _log(
        project.id, code, "olusturma", f"{code} projesi oluşturuldu", user, yeni_durum=project.durum
    )
    return project


@router.get("/projects/{proje_id}", response_model=ProjectDetail)
async def get_project(proje_id: str, user: dict = Depends(require("proje:goruntule"))):
    doc = await _get_project(proje_id)
    items = await db.project_items.find({"proje_id": proje_id}).sort("created_at", 1).to_list(500)
    crates = await db.project_crates.find({"proje_id": proje_id}).sort("created_at", 1).to_list(500)
    acts = await db.activities.find({"proje_id": proje_id}).sort("created_at", -1).to_list(300)
    return ProjectDetail(
        project=await _mask(Project(**doc), user),
        kalemler=[ProjectItem(**_aware(i)) for i in items],
        sandiklar=[ProjectCrate(**_aware(c)) for c in crates],
        hareketler=[Activity(**_aware(a)) for a in acts],
    )


@router.put("/projects/{proje_id}", response_model=Project)
async def update_project(
    proje_id: str, payload: ProjectUpdate, user: dict = Depends(require("proje:duzenle"))
):
    doc = await _get_project(proje_id)
    if payload.durum not in await stage_keys():
        raise HTTPException(status_code=400, detail="Geçersiz aşama")
    data = payload.model_dump()
    data["updated_at"] = now_utc()
    await db.projects.update_one({"id": proje_id}, {"$set": data})
    if doc["durum"] != payload.durum:
        labels = await stage_labels()
        await _log(
            proje_id,
            doc["proje_kodu"],
            "asama",
            f"Aşama {labels.get(doc['durum'], doc['durum'])} → {labels.get(payload.durum, payload.durum)}",
            user,
            eski_durum=doc["durum"],
            yeni_durum=payload.durum,
        )
    else:
        await _log(proje_id, doc["proje_kodu"], "guncelleme", "Proje bilgileri güncellendi", user)
    return Project(**await _get_project(proje_id))


@router.patch("/projects/{proje_id}/stage", response_model=Project)
async def update_stage(proje_id: str, payload: StageUpdate, user: dict = Depends(require("asama:degistir"))):
    doc = await _get_project(proje_id)
    keys = await stage_keys()
    if payload.durum not in keys:
        raise HTTPException(status_code=400, detail="Geçersiz aşama")
    patch: dict = {"durum": payload.durum, "updated_at": now_utc()}
    # stage transitions stamp their own milestone date, server anchored
    if payload.durum == "musteri_onayi" and not doc.get("musteri_onay_tarihi"):
        patch["musteri_onay_tarihi"] = today_iso()
    if payload.durum == "uretim" and not doc.get("tedarikci_onay_tarihi"):
        patch["tedarikci_onay_tarihi"] = today_iso()
    if payload.durum == "yuklendi_sevk" and not doc.get("sevk_tarihi"):
        patch["sevk_tarihi"] = today_iso()
    # son aşama (listenin sonu) projeyi arşive alır
    if payload.durum == keys[-1]:
        patch["arsiv"] = True
    await db.projects.update_one({"id": proje_id}, {"$set": patch})
    labels = await stage_labels()
    mesaj = f"Aşama {labels.get(doc['durum'], doc['durum'])} → {labels.get(payload.durum, payload.durum)}"
    if payload.not_:
        mesaj += f" — {payload.not_}"
    await _log(
        proje_id,
        doc["proje_kodu"],
        "asama",
        mesaj,
        user,
        eski_durum=doc["durum"],
        yeni_durum=payload.durum,
    )
    return Project(**await _get_project(proje_id))


@router.patch("/projects/{proje_id}/archive", response_model=Project)
async def toggle_archive(proje_id: str, user: dict = Depends(require("proje:sil"))):
    doc = await _get_project(proje_id)
    yeni = not doc.get("arsiv", False)
    await db.projects.update_one(
        {"id": proje_id}, {"$set": {"arsiv": yeni, "updated_at": now_utc()}}
    )
    await _log(
        proje_id,
        doc["proje_kodu"],
        "guncelleme",
        "Proje arşivlendi" if yeni else "Proje arşivden çıkarıldı",
        user,
    )
    return Project(**await _get_project(proje_id))


@router.delete("/projects/{proje_id}")
async def delete_project(proje_id: str, user: dict = Depends(require("proje:sil"))):
    """Proje çöp kutusuna taşınır — 30 gün içinde geri getirilebilir."""
    from routers.trash import move_to_trash

    doc = await _get_project(proje_id)
    await move_to_trash(doc, user)
    return {"ok": True, "cop_kutusu": True}


# ---------------- accounting ----------------
@router.put("/projects/{proje_id}/muhasebe", response_model=Project)
async def update_muhasebe(proje_id: str, payload: Muhasebe, user: dict = Depends(require("muhasebe:duzenle"))):
    doc = await _get_project(proje_id)
    muhasebe = compute_muhasebe(payload)
    await db.projects.update_one(
        {"id": proje_id},
        {"$set": {"muhasebe": muhasebe.model_dump(by_alias=True), "updated_at": now_utc()}},
    )
    await _log(
        proje_id,
        doc["proje_kodu"],
        "muhasebe",
        f"Muhasebe güncellendi — Tahsilat {muhasebe.toplam_tahsilat:,.2f} {doc.get('para_birimi', '')}, Kalan {muhasebe.kalan_bakiye:,.2f}",
        user,
    )
    return Project(**await _get_project(proje_id))


# ---------------- items ----------------
@router.post("/projects/{proje_id}/kalemler", response_model=ProjectItem)
async def add_item(proje_id: str, payload: ItemBase, user: dict = Depends(require("kalem:yonet"))):
    doc = await _get_project(proje_id)
    item = ProjectItem(proje_id=proje_id, **payload.model_dump())
    await db.project_items.insert_one(item.model_dump())
    await _refresh_item_count(proje_id)
    await _log(
        proje_id, doc["proje_kodu"], "kalem", f"Kalem eklendi: {item.urun} ({item.adet} adet)", user
    )
    return item


@router.put("/kalemler/{item_id}", response_model=ProjectItem)
async def update_item(item_id: str, payload: ItemBase, user: dict = Depends(require("kalem:yonet"))):
    existing = await db.project_items.find_one({"id": item_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Kalem bulunamadı")
    await db.project_items.update_one({"id": item_id}, {"$set": payload.model_dump()})
    doc = await db.project_items.find_one({"id": item_id})
    project = await db.projects.find_one({"id": existing["proje_id"]})
    await _log(
        existing["proje_id"],
        (project or {}).get("proje_kodu", ""),
        "kalem",
        f"Kalem güncellendi: {payload.urun}",
        user,
    )
    return ProjectItem(**_aware(doc or {}))


@router.delete("/kalemler/{item_id}")
async def delete_item(item_id: str, user: dict = Depends(require("kalem:yonet"))):
    existing = await db.project_items.find_one({"id": item_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Kalem bulunamadı")
    await db.project_items.delete_one({"id": item_id})
    await _refresh_item_count(existing["proje_id"])
    project = await db.projects.find_one({"id": existing["proje_id"]})
    await _log(
        existing["proje_id"],
        (project or {}).get("proje_kodu", ""),
        "kalem",
        f"Kalem silindi: {existing.get('urun', '')}",
        user,
    )
    return {"ok": True}


# ---------------- crates ----------------
@router.post("/projects/{proje_id}/sandiklar", response_model=ProjectCrate)
async def add_crate(proje_id: str, payload: CrateBase, user: dict = Depends(require("sandik:yonet"))):
    doc = await _get_project(proje_id)
    crate = compute_cbm(ProjectCrate(proje_id=proje_id, **payload.model_dump()))
    await db.project_crates.insert_one(crate.model_dump())
    await _log(
        proje_id,
        doc["proje_kodu"],
        "sandik",
        f"Sandık eklendi: {crate.sandik_no} — {crate.hacim_cbm} m³ / {crate.brut_kg} kg",
        user,
    )
    return crate


@router.delete("/sandiklar/{crate_id}")
async def delete_crate(crate_id: str, user: dict = Depends(require("sandik:yonet"))):
    existing = await db.project_crates.find_one({"id": crate_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Sandık bulunamadı")
    await db.project_crates.delete_one({"id": crate_id})
    project = await db.projects.find_one({"id": existing["proje_id"]})
    await _log(
        existing["proje_id"],
        (project or {}).get("proje_kodu", ""),
        "sandik",
        f"Sandık silindi: {existing.get('sandik_no', '')}",
        user,
    )
    return {"ok": True}


# ---------------- notes ----------------
@router.post("/projects/{proje_id}/notlar", response_model=Activity)
async def add_note(proje_id: str, payload: NoteInput, user: dict = Depends(current_user)):
    doc = await _get_project(proje_id)
    return await _log(proje_id, doc["proje_kodu"], "not", payload.mesaj, user)


# ---------------- dashboard ----------------
@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(user: dict = Depends(current_user)):
    docs = [_aware(d) for d in await db.projects.find().to_list(1000)]
    projects = [Project(**d) for d in docs]
    aktif = [p for p in projects if not p.arsiv]

    asamalar: List[StageCount] = []
    for stage in STAGES:
        group = [p for p in projects if p.durum == stage]
        asamalar.append(
            StageCount(
                durum=stage,
                label=STAGE_LABELS[stage],
                adet=len(group),
                tutar=round(sum(p.muhasebe.transfer_dahil_toplam_satis for p in group), 2),
            )
        )

    para: List[StageCount] = []
    for cur in sorted({p.para_birimi for p in projects if p.para_birimi}):
        group = [p for p in projects if p.para_birimi == cur]
        para.append(
            StageCount(
                durum=cur,
                label=cur,
                adet=len(group),
                tutar=round(sum(p.muhasebe.transfer_dahil_toplam_satis for p in group), 2),
            )
        )

    kar_list = [p.muhasebe.kar_yuzdesi for p in projects if p.muhasebe.satis > 0]
    yaklasan = sorted(
        [p for p in aktif if p.sevk_tarihi or p.termin_tarihi],
        key=lambda p: p.sevk_tarihi or p.termin_tarihi or "9999",
    )[:8]
    acts = await db.activities.find().sort("created_at", -1).to_list(15)
    uyarilar = build_alerts(aktif)

    finans = "muhasebe:goruntule" in await user_permissions(user)
    if not finans:
        # Yetkisiz kullanıcıya hiçbir finansal kırılım sızmaz (adetler kalır).
        for row in asamalar + para:
            row.tutar = 0.0
        yaklasan = [p.model_copy(update={"muhasebe": Muhasebe()}) for p in yaklasan]
    return DashboardStats(
        toplam_proje=len(projects),
        aktif_proje=len(aktif),
        arsiv_proje=len(projects) - len(aktif),
        toplam_satis=round(sum(p.muhasebe.transfer_dahil_toplam_satis for p in projects), 2)
        if finans
        else 0.0,
        toplam_tahsilat=round(sum(p.muhasebe.toplam_tahsilat for p in projects), 2)
        if finans
        else 0.0,
        kalan_bakiye=round(sum(p.muhasebe.kalan_bakiye for p in projects), 2) if finans else 0.0,
        net_kar=round(sum(p.muhasebe.net_kar for p in projects), 2) if finans else 0.0,
        ortalama_kar_yuzdesi=(round(sum(kar_list) / len(kar_list), 2) if kar_list else 0.0)
        if finans
        else 0.0,
        asamalar=asamalar,
        para_birimi_dagilimi=para,
        yaklasan_sevkiyatlar=yaklasan,
        son_hareketler=[Activity(**_aware(a)) for a in acts],
        uyarilar=uyarilar,
        geciken_adet=len([u for u in uyarilar if u.seviye == "gecikti"]),
        yaklasan_adet=len([u for u in uyarilar if u.seviye in ("bugun", "yaklasiyor")]),
    )


@router.get("/alerts", response_model=List[DeadlineAlert])
async def alerts(user: dict = Depends(current_user)):
    docs = await db.projects.find({"arsiv": False}).to_list(1000)
    return build_alerts([Project(**_aware(d)) for d in docs])


@router.get("/stages", response_model=List[StageCount])
async def stages():
    """Stage vocabulary — the single source of truth the frontend mirrors."""
    return [
        StageCount(durum=s, label=STAGE_LABELS[s], adet=i + 1, tutar=0.0)
        for i, s in enumerate(STAGES)
    ]
