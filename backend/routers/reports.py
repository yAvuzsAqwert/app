"""Daily report + XLSX export."""

import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from lib.auth import current_user
from lib.dates import today_iso
from lib.db import db
from models.schemas import STAGE_LABELS, Activity, DailyReport, Project

router = APIRouter(prefix="/reports", tags=["reports"])


def _aware(doc: dict) -> dict:
    for key in ("created_at", "updated_at"):
        value = doc.get(key)
        if isinstance(value, datetime) and value.tzinfo is None:
            doc[key] = value.replace(tzinfo=timezone.utc)
    return doc


async def _collect(tarih: str) -> DailyReport:
    acts = [
        Activity(**_aware(a))
        for a in await db.activities.find({"gun": tarih}).sort("created_at", -1).to_list(500)
    ]
    yeni_docs = await db.projects.find({"proje_tarihi": tarih}).to_list(200)
    sevk_docs = await db.projects.find({"sevk_tarihi": tarih}).to_list(200)
    aktif = await db.projects.count_documents({"arsiv": False})
    yeni = [Project(**_aware(d)) for d in yeni_docs]
    sevk = [Project(**_aware(d)) for d in sevk_docs]
    return DailyReport(
        tarih=tarih,
        yeni_projeler=yeni,
        asama_degisimleri=[a for a in acts if a.tip == "asama"],
        sevk_edilenler=sevk,
        tum_hareketler=acts,
        gun_satis=round(sum(p.muhasebe.transfer_dahil_toplam_satis for p in yeni), 2),
        gun_tahsilat=round(sum(p.muhasebe.toplam_tahsilat for p in sevk), 2),
        aktif_proje=aktif,
    )


@router.get("/daily", response_model=DailyReport)
async def daily_report(
    tarih: Optional[str] = Query(default=None), user: dict = Depends(current_user)
):
    return await _collect(tarih or today_iso())


@router.get("/daily/export")
async def export_daily(
    tarih: Optional[str] = Query(default=None), user: dict = Depends(current_user)
):
    gun = tarih or today_iso()
    report = await _collect(gun)
    projects = [
        Project(**_aware(d))
        for d in await db.projects.find().sort("proje_tarihi", -1).to_list(1000)
    ]

    wb = Workbook()
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="0F172A")

    def sheet(title: str, headers: list[str], rows: list[list]):
        ws = wb.create_sheet(title)
        ws.append(headers)
        for cell in ws[1]:
            cell.font = head_font
            cell.fill = head_fill
            cell.alignment = Alignment(horizontal="center")
        for row in rows:
            ws.append(row)
        for idx, header in enumerate(headers, start=1):
            ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = max(
                14, min(38, len(header) + 6)
            )
        return ws

    wb.remove(wb.active)

    sheet(
        f"Gun Ozeti",
        ["Rapor Tarihi", "Yeni Proje", "Asama Degisimi", "Sevk Edilen", "Aktif Proje", "Gun Satis"],
        [
            [
                gun,
                len(report.yeni_projeler),
                len(report.asama_degisimleri),
                len(report.sevk_edilenler),
                report.aktif_proje,
                report.gun_satis,
            ]
        ],
    )

    sheet(
        "Gun Hareketleri",
        ["Saat", "Proje Kodu", "Tip", "Aciklama", "Kullanici"],
        [
            [a.created_at.strftime("%H:%M"), a.proje_kodu, a.tip, a.mesaj, a.kullanici]
            for a in report.tum_hareketler
        ],
    )

    sheet(
        "Projeler",
        [
            "Proje Kodu",
            "Firma",
            "Musteri",
            "Ulke",
            "Proje Adi",
            "Tarih",
            "Asama",
            "Tedarikci",
            "Para Birimi",
            "Satis",
            "Alis",
            "Iskonto",
            "Transfer",
            "Toplam Satis",
            "Net Kar",
            "Kar %",
            "Odeme Durumu",
            "Tahsilat",
            "Kalan Bakiye",
            "Sevk Tarihi",
            "Arsiv",
        ],
        [
            [
                p.proje_kodu,
                p.firma,
                p.musteri,
                p.ulke,
                p.proje_adi,
                p.proje_tarihi,
                STAGE_LABELS.get(p.durum, p.durum),
                p.tedarikci,
                p.para_birimi,
                p.muhasebe.satis,
                p.muhasebe.alis,
                p.muhasebe.iskonto_tutari,
                p.muhasebe.transfer_ucreti,
                p.muhasebe.transfer_dahil_toplam_satis,
                p.muhasebe.net_kar,
                p.muhasebe.kar_yuzdesi,
                p.muhasebe.odeme_durumu,
                p.muhasebe.toplam_tahsilat,
                p.muhasebe.kalan_bakiye,
                p.sevk_tarihi or "",
                "Evet" if p.arsiv else "Hayir",
            ]
            for p in projects
        ],
    )

    items = await db.project_items.find().to_list(2000)
    code_by_id = {p.id: p.proje_kodu for p in projects}
    sheet(
        "Proje Kalemleri",
        [
            "Proje Kodu",
            "Urun",
            "Adet",
            "Genislik (mm)",
            "Acilim (mm)",
            "Yapi Rengi",
            "Panel Rengi",
            "Aydinlatma",
            "Cam Kombinasyonu",
            "Tedarikci",
            "Birim Fiyat",
        ],
        [
            [
                code_by_id.get(i.get("proje_id", ""), ""),
                i.get("urun", ""),
                i.get("adet", 0),
                i.get("genislik_mm", 0),
                i.get("acilim_mm", 0),
                i.get("yapi_rengi", ""),
                i.get("panel_rengi", ""),
                i.get("aydinlatma", ""),
                i.get("cam_kombinasyonu", ""),
                i.get("tedarikci", ""),
                i.get("birim_fiyat", 0),
            ]
            for i in items
        ],
    )

    crates = await db.project_crates.find().to_list(2000)
    sheet(
        "Sandik Listesi",
        [
            "Proje Kodu",
            "Sandik No",
            "Icerik",
            "Taban (cm)",
            "Uzunluk (cm)",
            "Yukseklik (cm)",
            "Adet",
            "Hacim (m3)",
            "Brut (kg)",
            "Tedarikci",
        ],
        [
            [
                code_by_id.get(c.get("proje_id", ""), ""),
                c.get("sandik_no", ""),
                c.get("icerik", ""),
                c.get("taban_cm", 0),
                c.get("uzunluk_cm", 0),
                c.get("yukseklik_cm", 0),
                c.get("adet", 0),
                c.get("hacim_cbm", 0),
                c.get("brut_kg", 0),
                c.get("tedarikci", ""),
            ]
            for c in crates
        ],
    )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="pergola-rapor-{gun}.xlsx"'},
    )
