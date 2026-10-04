"""Proforma fatura PDF'i — reportlab + Nunito (Türkçe karakter desteği)."""

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
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from lib.auth import current_user
from lib.catalog import stage_labels
from lib.db import db, get_db
from lib.permissions import require
from models.schemas import STAGE_LABELS
from routers.revisions import snapshot

router = APIRouter(tags=["proforma"])

COMPANY = os.environ.get("COMPANY_NAME", "DIAGONAL")
# Türkçe glif desteği: font depoya gömülüdür (üretim imajında sistem fontu olmayabilir).
BUNDLED_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")
FONT_DIRS = [BUNDLED_FONT_DIR, "/usr/share/fonts/truetype/liberation"]
ACCENT = colors.HexColor("#F97316")
DARK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#CBD5E1")

_FONTS_READY = False

IMAGE_EXT = {"png", "jpg", "jpeg", "webp", "gif"}
def _bucket() -> AsyncIOMotorGridFSBucket:
    """Her istekte servis eden event loop içinde oluşturulur."""
    return AsyncIOMotorGridFSBucket(get_db(), bucket_name="evraklar")


async def _drawing_flowables(proje_id: str, body, small) -> list:
    """'Çizim' kategorisindeki resim evrakları → proformanın sonunda ayrı sayfa."""
    docs = (
        await db.documents.find({"proje_id": proje_id, "kategori": "cizim"})
        .sort("created_at", 1)
        .to_list(20)
    )
    cells: list = []
    for meta in docs:
        name = meta.get("dosya_adi", "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in IMAGE_EXT:
            continue
        try:
            stream = await _bucket().open_download_stream(ObjectId(meta["file_id"]))
            data = await stream.read()
            reader = ImageReader(io.BytesIO(data))
            iw, ih = reader.getSize()
        except Exception:
            continue
        max_w, max_h = 86 * mm, 70 * mm
        scale = min(max_w / iw, max_h / ih)
        img = Image(io.BytesIO(data), width=iw * scale, height=ih * scale)
        img.hAlign = "CENTER"
        caption = meta.get("aciklama") or name
        cells.append([img, Paragraph(f"<font size=7.5 color='#64748B'>{caption}</font>", small)])

    if not cells:
        return []

    flow: list = [
        PageBreak(),
        Paragraph("<b>TEKNİK ÇİZİMLER</b>", body),
        Spacer(1, 1.5 * mm),
    ]
    for i in range(0, len(cells), 2):
        pair = cells[i : i + 2]
        row_imgs = [c[0] for c in pair]
        row_caps = [c[1] for c in pair]
        while len(row_imgs) < 2:
            row_imgs.append(Paragraph("", small))
            row_caps.append(Paragraph("", small))
        table = Table([row_imgs, row_caps], colWidths=[91 * mm, 91 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOX", (0, 0), (0, -1), 0.5, LINE),
                    *([("BOX", (1, 0), (1, -1), 0.5, LINE)] if len(pair) > 1 else []),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        flow += [KeepTogether([table, Spacer(1, 4 * mm)])]
    return flow


def _register_fonts() -> tuple[str, str]:
    """Türkçe karakterler (ı, ş, ğ, İ, Ö, Ç…) için TTF şart — Helvetica bunları basamaz."""
    global _FONTS_READY
    if _FONTS_READY:
        return ("LibSans", "LibSans-Bold")
    for directory in FONT_DIRS:
        regular = os.path.join(directory, "Nunito-Regular.ttf")
        bold = os.path.join(directory, "Nunito-Bold.ttf")
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont("LibSans", regular))
            pdfmetrics.registerFont(TTFont("LibSans-Bold", bold))
            pdfmetrics.registerFontFamily("LibSans", normal="LibSans", bold="LibSans-Bold")
            _FONTS_READY = True
            return ("LibSans", "LibSans-Bold")
    raise HTTPException(
        status_code=500,
        detail="PDF fontu bulunamadı (assets/fonts/Nunito-*.ttf) — Türkçe karakterler basılamaz",
    )


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


async def _build_proforma_pdf(project: dict, items: list[dict], labels: dict) -> io.BytesIO:
    font, bold = _register_fonts()
    proje_id = project["id"]
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
    from models.schemas import Muhasebe, compute_muhasebe

    raw = dict(project.get("muhasebe", {}) or {})
    # Satış girilmemişse kalem ara toplamı esas alınır; tüm türevler anlık hesaplanır.
    if not float(raw.get("satis") or 0):
        raw["satis"] = ara_toplam
    m = compute_muhasebe(Muhasebe(**raw))
    odeme_satirlari = [
        [
            f"{i}. Ödeme" + (f" ({o.tarih})" if o.tarih else ""),
            _money(o.tutar, cur),
        ]
        for i, o in enumerate(m.odemeler, start=1)
        if o.tutar > 0
    ]
    total_rows = [
        ["Kalemler Ara Toplamı", _money(ara_toplam, cur)],
        ["Satış Tutarı", _money(m.satis, cur)],
        ["İskonto", f"- {_money(m.iskonto_tutari, cur)}"],
        ["Transfer / Navlun", _money(m.transfer_ucreti, cur)],
        ["GENEL TOPLAM", _money(m.transfer_dahil_toplam_satis, cur)],
        *odeme_satirlari,
        ["Toplam Tahsilat", _money(m.toplam_tahsilat, cur)],
        ["KALAN BAKİYE", _money(m.kalan_bakiye, cur)],
    ]
    totals = Table(
        [
            [
                Paragraph(
                    f"<b>{a}</b>" if a in ("GENEL TOPLAM", "KALAN BAKİYE") else a, body
                ),
                Paragraph(f"<b>{b}</b>", h_right),
            ]
            for a, b in total_rows
        ],
        colWidths=[60 * mm, 42 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, -1), (-1, -1), 1.2, ACCENT),
                ("LINEABOVE", (0, 4), (-1, 4), 1.2, ACCENT),
                ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#FFF7ED")),
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

    flow += await _drawing_flowables(proje_id, body, small)

    doc.build(flow)
    buf.seek(0)
    return buf


@router.get("/projects/{proje_id}/proforma")
async def proforma_pdf(proje_id: str, user: dict = Depends(require("proforma:olustur"))):
    project = await db.projects.find_one({"id": proje_id})
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    items = await db.project_items.find({"proje_id": proje_id}).sort("created_at", 1).to_list(500)
    # PDF her alındığında proformanın o anki hali revizyon olarak saklanır
    await snapshot(proje_id, "pdf", "Proforma PDF indirildi", user)
    buf = await _build_proforma_pdf(project, items, await stage_labels())
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="proforma-{project.get("proje_kodu", "")}.pdf"'
        },
    )
