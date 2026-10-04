"""Proforma fatura PDF'i — reportlab + Liberation Sans (Türkçe karakter desteği)."""

import io
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lib.auth import current_user
from lib.catalog import stage_labels
from lib.db import db
from models.schemas import STAGE_LABELS
from routers.revisions import snapshot

router = APIRouter(tags=["proforma"])

COMPANY = os.environ.get("COMPANY_NAME", "DIAGONAL")
FONT_DIR = "/usr/share/fonts/truetype/liberation"
ACCENT = colors.HexColor("#F97316")
DARK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#CBD5E1")

_FONTS_READY = False


def _register_fonts() -> tuple[str, str]:
    """Liberation Sans covers Turkish glyphs; Helvetica does not."""
    global _FONTS_READY
    regular, bold = f"{FONT_DIR}/LiberationSans-Regular.ttf", f"{FONT_DIR}/LiberationSans-Bold.ttf"
    if not _FONTS_READY and os.path.exists(regular) and os.path.exists(bold):
        pdfmetrics.registerFont(TTFont("LibSans", regular))
        pdfmetrics.registerFont(TTFont("LibSans-Bold", bold))
        _FONTS_READY = True
    return ("LibSans", "LibSans-Bold") if _FONTS_READY else ("Helvetica", "Helvetica-Bold")


def _money(value: float, currency: str = "") -> str:
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} {currency}".strip()


def _tr_date(value: str | None) -> str:
    if not value:
        return "-"
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return value


@router.get("/projects/{proje_id}/proforma")
async def proforma_pdf(proje_id: str, user: dict = Depends(current_user)):
    project = await db.projects.find_one({"id": proje_id})
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    items = await db.project_items.find({"proje_id": proje_id}).sort("created_at", 1).to_list(500)
    # PDF her alındığında proformanın o anki hali revizyon olarak saklanır
    await snapshot(proje_id, "pdf", "Proforma PDF indirildi", user)
    labels = await stage_labels()

    font, bold = _register_fonts()
    cur = project.get("para_birimi", "")
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName=font, fontSize=8.5, leading=11)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, textColor=MUTED, leading=9.5)
    h_right = ParagraphStyle("hr", parent=body, alignment=TA_RIGHT)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        title=f"Proforma {project.get('proje_kodu', '')}",
    )
    flow = []

    # ---- header
    header = Table(
        [
            [
                Paragraph(
                    f"<font size=20 color='#0F172A'><b>{COMPANY}</b></font><br/>"
                    f"<font size=8 color='#64748B'>Pergola · Tente · Sürme &amp; Giyotin Cam Sistemleri</font>",
                    body,
                ),
                Paragraph(
                    f"<font size=15 color='#F97316'><b>PROFORMA FATURA</b></font><br/>"
                    f"<font size=8.5><b>No:</b> {project.get('proje_kodu', '')}<br/>"
                    f"<b>Tarih:</b> {_tr_date(project.get('proje_tarihi'))}<br/>"
                    f"<b>Para Birimi:</b> {cur}</font>",
                    h_right,
                ),
            ]
        ],
        colWidths=[105 * mm, 77 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 1.4, ACCENT),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ]
        )
    )
    flow += [header, Spacer(1, 7 * mm)]

    # ---- parties
    parties = Table(
        [
            [
                Paragraph(
                    f"<font size=7.5 color='#64748B'><b>ALICI / MÜŞTERİ</b></font><br/>"
                    f"<b>{project.get('firma') or '-'}</b><br/>"
                    f"{project.get('musteri') or '-'}<br/>{project.get('ulke') or '-'}",
                    body,
                ),
                Paragraph(
                    f"<font size=7.5 color='#64748B'><b>PROJE BİLGİSİ</b></font><br/>"
                    f"<b>{project.get('proje_adi') or '-'}</b><br/>"
                    f"Montaj: {project.get('montaj_tipi') or '-'}<br/>"
                    f"Aşama: {labels.get(project.get('durum', ''), '-')}",
                    body,
                ),
                Paragraph(
                    f"<font size=7.5 color='#64748B'><b>TERMİN / SEVK</b></font><br/>"
                    f"Termin: {_tr_date(project.get('termin_tarihi'))}<br/>"
                    f"Sevk: {_tr_date(project.get('sevk_tarihi'))}<br/>"
                    f"Tedarikçi: {project.get('tedarikci') or '-'}",
                    body,
                ),
            ]
        ],
        colWidths=[62 * mm, 62 * mm, 58 * mm],
    )
    parties.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow += [parties, Spacer(1, 6 * mm)]

    # ---- items
    rows = [
        [
            Paragraph("<b>#</b>", small),
            Paragraph("<b>ÜRÜN / TEKNİK ÖZELLİK</b>", small),
            Paragraph("<b>ÖLÇÜ (mm)</b>", small),
            Paragraph("<b>ADET</b>", small),
            Paragraph("<b>BİRİM FİYAT</b>", small),
            Paragraph("<b>TUTAR</b>", small),
        ]
    ]
    ara_toplam = 0.0
    for i, k in enumerate(items, start=1):
        tutar = (k.get("adet") or 0) * (k.get("birim_fiyat") or 0)
        ara_toplam += tutar
        specs = [
            s
            for s in [
                k.get("yapi_rengi") and f"Yapı: {k['yapi_rengi']}",
                k.get("panel_rengi") and f"Panel: {k['panel_rengi']}",
                k.get("cam_kombinasyonu") and f"Cam: {k['cam_kombinasyonu']}",
                k.get("cam_rengi") and f"Cam Rengi: {k['cam_rengi']}",
                k.get("aydinlatma") and f"Aydınlatma: {k['aydinlatma']}",
                k.get("led_strip_mtul") and f"LED Strip: {k['led_strip_mtul']} mtül",
                k.get("led_spot_adet") and f"LED Spot: {k['led_spot_adet']} adet",
                k.get("zip_kumasi") and f"Zip Kumaş: {k['zip_kumasi']}",
                k.get("pergola_kumasi") and f"Pergola Kumaş: {k['pergola_kumasi']}",
            ]
            if s
        ]
        rows.append(
            [
                Paragraph(str(i), small),
                Paragraph(
                    f"<b>{k.get('urun', '-')}</b>"
                    + (f"<br/><font size=7 color='#64748B'>{' · '.join(specs)}</font>" if specs else ""),
                    body,
                ),
                Paragraph(
                    f"{k.get('genislik_mm') or 0:.0f} × {k.get('acilim_mm') or 0:.0f}", small
                ),
                Paragraph(str(k.get("adet") or 0), small),
                Paragraph(_money(k.get("birim_fiyat") or 0), small),
                Paragraph(f"<b>{_money(tutar)}</b>", small),
            ]
        )
    if not items:
        rows.append([Paragraph("", small), Paragraph("Kalem girilmemiş.", body), "", "", "", ""])

    table = Table(rows, colWidths=[8 * mm, 76 * mm, 25 * mm, 14 * mm, 28 * mm, 31 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    flow += [table, Spacer(1, 5 * mm)]

    # ---- totals (accounting is the source of truth; items are the breakdown)
    m = project.get("muhasebe", {}) or {}
    satis = float(m.get("satis") or 0) or ara_toplam
    iskonto = float(m.get("iskonto_tutari") or 0)
    transfer = float(m.get("transfer_ucreti") or 0)
    genel = satis - iskonto + transfer
    total_rows = [
        ["Kalemler Ara Toplamı", _money(ara_toplam, cur)],
        ["Satış Tutarı", _money(satis, cur)],
        ["İskonto", f"- {_money(iskonto, cur)}"],
        ["Transfer / Navlun", _money(transfer, cur)],
        ["GENEL TOPLAM", _money(genel, cur)],
    ]
    totals = Table(
        [[Paragraph(f"<b>{a}</b>" if a == "GENEL TOPLAM" else a, body), Paragraph(f"<b>{b}</b>", h_right)] for a, b in total_rows],
        colWidths=[60 * mm, 42 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, -1), (-1, -1), 1.2, ACCENT),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFF7ED")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow += [totals, Spacer(1, 7 * mm)]

    # ---- bank / notes
    notes = Table(
        [
            [
                Paragraph(
                    "<font size=7.5 color='#64748B'><b>BANKA / ÖDEME BİLGİLERİ</b></font><br/>"
                    f"Hesap Sahibi: {COMPANY}<br/>Banka: ____________________<br/>"
                    "IBAN: ____________________<br/>SWIFT: ____________________",
                    body,
                ),
                Paragraph(
                    "<font size=7.5 color='#64748B'><b>NOT / ŞARTLAR</b></font><br/>"
                    f"{project.get('notlar') or 'Fiyatlar teklif tarihinden itibaren 15 gün geçerlidir.'}<br/>"
                    f"Teslim: {project.get('montaj_tipi') or '-'} · "
                    f"Lojistik: {project.get('lojistik_firmasi') or '-'}",
                    body,
                ),
            ]
        ],
        colWidths=[91 * mm, 91 * mm],
    )
    notes.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow += [
        KeepTogether([notes, Spacer(1, 6 * mm)]),
        Paragraph(
            f"Bu belge {COMPANY} tarafından {_tr_date(project.get('proje_tarihi'))} tarihinde "
            f"düzenlenmiştir. Proforma fatura olup yasal fatura yerine geçmez.",
            small,
        ),
    ]

    doc.build(flow)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="proforma-{project.get("proje_kodu", "")}.pdf"'
        },
    )
