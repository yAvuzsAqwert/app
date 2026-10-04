"""Sandık etiketleri — A4 sayfaya 2×2 yerleşimle 4 etiket."""

import io
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from lib.auth import current_user
from lib.catalog import stage_labels
from lib.db import db
from routers.proforma import _register_fonts

router = APIRouter(tags=["labels"])

COMPANY = os.environ.get("COMPANY_NAME", "DIAGONAL")
ACCENT = colors.HexColor("#F97316")
DARK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")

PAGE_W, PAGE_H = A4
MARGIN = 8 * mm
COLS, ROWS = 2, 2
CELL_W = (PAGE_W - 2 * MARGIN) / COLS
CELL_H = (PAGE_H - 2 * MARGIN) / ROWS


def _draw_label(c: canvas.Canvas, x: float, y: float, project: dict, crate: dict, font: str, bold: str, labels: dict) -> None:
    """Tek etiket — sol alt köşe (x, y)."""
    pad = 6 * mm
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.8)
    c.setDash(2, 2)
    c.rect(x + 2 * mm, y + 2 * mm, CELL_W - 4 * mm, CELL_H - 4 * mm)
    c.setDash()

    inner_x = x + pad
    top = y + CELL_H - pad

    # başlık bandı
    c.setFillColor(DARK)
    c.rect(inner_x, top - 11 * mm, CELL_W - 2 * pad, 11 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(bold, 13)
    c.drawString(inner_x + 3 * mm, top - 7.5 * mm, COMPANY)
    c.setFillColor(ACCENT)
    c.setFont(bold, 9)
    c.drawRightString(inner_x + CELL_W - 2 * pad - 3 * mm, top - 7.3 * mm, "SEVK ETİKETİ")

    cursor = top - 11 * mm - 9 * mm

    # büyük sandık numarası
    c.setFillColor(ACCENT)
    c.setFont(bold, 26)
    c.drawString(inner_x, cursor, crate.get("sandik_no") or "SND-??")
    c.setFillColor(MUTED)
    c.setFont(font, 8.5)
    c.drawRightString(
        inner_x + CELL_W - 2 * pad,
        cursor + 3 * mm,
        f"{crate.get('adet') or 1} koli/sandık",
    )
    cursor -= 9 * mm

    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.2)
    c.line(inner_x, cursor, inner_x + CELL_W - 2 * pad, cursor)
    cursor -= 6 * mm

    def row(label: str, value: str, size: float = 9.5) -> None:
        nonlocal cursor
        c.setFillColor(MUTED)
        c.setFont(font, 7.5)
        c.drawString(inner_x, cursor, label)
        c.setFillColor(DARK)
        c.setFont(bold, size)
        c.drawString(inner_x + 26 * mm, cursor, value[:42])
        cursor -= 6.2 * mm

    row("PROJE", project.get("proje_kodu", "-"))
    row("MÜŞTERİ", project.get("musteri") or project.get("firma") or "-")
    row("ÜLKE", project.get("ulke") or "-")
    row("İÇERİK", crate.get("icerik") or "-", 8.5)

    cursor -= 1 * mm
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.rect(inner_x, cursor - 15 * mm, CELL_W - 2 * pad, 16 * mm, fill=1, stroke=0)
    box_y = cursor - 4 * mm
    taban = crate.get("taban_cm") or 0
    uzunluk = crate.get("uzunluk_cm") or 0
    yukseklik = crate.get("yukseklik_cm") or 0
    metrics = [
        ("ÖLÇÜ (cm)", f"{uzunluk:.0f} × {taban:.0f} × {yukseklik:.0f}"),
        ("HACİM", f"{crate.get('hacim_cbm') or 0} m³"),
        ("BRÜT", f"{crate.get('brut_kg') or 0:.0f} kg"),
    ]
    width_each = (CELL_W - 2 * pad) / 3
    for i, (lbl, val) in enumerate(metrics):
        cx = inner_x + i * width_each + 3 * mm
        c.setFillColor(MUTED)
        c.setFont(font, 7)
        c.drawString(cx, box_y, lbl)
        c.setFillColor(DARK)
        c.setFont(bold, 11)
        c.drawString(cx, box_y - 6 * mm, val)

    cursor -= 20 * mm
    c.setFillColor(MUTED)
    c.setFont(font, 7.5)
    c.drawString(
        inner_x,
        cursor,
        f"Tedarikçi: {crate.get('tedarikci') or '-'}  ·  Aşama: {labels.get(project.get('durum', ''), '-')}",
    )
    c.drawString(
        inner_x,
        cursor - 4.5 * mm,
        f"Lojistik: {project.get('lojistik_firmasi') or '-'}  ·  Rez: {project.get('rezervasyon_kodu') or '-'}"
        f"  ·  Konteyner: {project.get('konteyner_no') or '-'}",
    )


@router.get("/projects/{proje_id}/sandik-etiketleri")
async def crate_labels(proje_id: str, user: dict = Depends(current_user)):
    project = await db.projects.find_one({"id": proje_id})
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    crates = await db.project_crates.find({"proje_id": proje_id}).sort("created_at", 1).to_list(400)
    if not crates:
        raise HTTPException(status_code=400, detail="Bu projede sandık kaydı yok")

    font, bold = _register_fonts()
    labels = await stage_labels()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Sandik Etiketleri {project.get('proje_kodu', '')}")

    for index, crate in enumerate(crates):
        slot = index % (COLS * ROWS)
        if slot == 0 and index:
            c.showPage()
        col = slot % COLS
        row_i = slot // COLS
        x = MARGIN + col * CELL_W
        y = PAGE_H - MARGIN - (row_i + 1) * CELL_H
        _draw_label(c, x, y, project, crate, font, bold, labels)

    c.showPage()
    c.save()
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="sandik-etiket-{project.get("proje_kodu", "")}.pdf"'
        },
    )
