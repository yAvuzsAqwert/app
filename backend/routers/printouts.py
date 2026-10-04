"""Yazdırılabilir çıktılar — proje dosyası (tüm detaylar) PDF'i.

Türkçe karakterler için depoya gömülü Nunito kullanılır
(bkz. routers/proforma.py::_register_fonts).
"""

import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lib.catalog import stage_labels
from lib.db import db
from lib.permissions import require, user_permissions
from routers.proforma import (
    ACCENT,
    COMPANY,
    DARK,
    LINE,
    MUTED,
    _money,
    _register_fonts,
    _tr_date,
)

router = APIRouter(tags=["printouts"])


def _section(title: str, style) -> Paragraph:
    return Paragraph(f"<b>{title}</b>", style)


def _kv_table(rows: list[tuple[str, str]], body, small, width: float = 182 * mm) -> Table:
    data = [
        [Paragraph(f"<font size=7.5 color='#64748B'>{k}</font>", small), Paragraph(v or "-", body)]
        for k, v in rows
    ]
    table = Table(data, colWidths=[46 * mm, width - 46 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


@router.get("/projects/{proje_id}/dosya.pdf")
async def project_dossier(proje_id: str, user: dict = Depends(require("proje:goruntule"))):
    """Projenin tüm detayları tek yazdırılabilir PDF: künye, kalemler, muhasebe, sandıklar, evraklar."""
    project = await db.projects.find_one({"id": proje_id})
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")

    yetkiler = await user_permissions(user)
    finans = "muhasebe:goruntule" in yetkiler
    labels = await stage_labels()
    items = await db.project_items.find({"proje_id": proje_id}).sort("created_at", 1).to_list(500)
    crates = await db.project_crates.find({"proje_id": proje_id}).sort("created_at", 1).to_list(200)
    docs = (
        await db.documents.find({"proje_id": proje_id}).sort("created_at", 1).to_list(200)
        if "evrak:goruntule" in yetkiler
        else []
    )
    revisions = (
        await db.proforma_versions.find({"proje_id": proje_id})
        .sort("versiyon", 1)
        .to_list(100)
    )

    font, bold = _register_fonts()
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName=font, fontSize=8.5, leading=11)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, textColor=MUTED, leading=9.5)
    head = ParagraphStyle("head", parent=body, fontName=bold, fontSize=11, textColor=DARK)
    h_right = ParagraphStyle("hr", parent=body, alignment=TA_RIGHT)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        title=f"Proje Dosyası {project.get('proje_kodu', '')}",
    )

    cur = project.get("para_birimi", "")
    muh = project.get("muhasebe", {}) or {}
    flow: list = []

    # Başlık
    header = Table(
        [
            [
                Paragraph(f"<font size=16><b>{COMPANY}</b></font>", head),
                Paragraph(
                    f"<b>PROJE DOSYASI</b><br/>{project.get('proje_kodu', '')}<br/>"
                    f"<font size=7.5 color='#64748B'>Çıktı: "
                    f"{datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')} UTC</font>",
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
                ("LINEBELOW", (0, 0), (-1, -1), 1, ACCENT),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow += [header, Spacer(1, 5 * mm)]

    # Künye
    flow += [
        _section("PROJE KÜNYESİ", head),
        Spacer(1, 1.5 * mm),
        _kv_table(
            [
                ("Proje Adı", project.get("proje_adi", "")),
                ("Firma / Bayi", project.get("firma", "")),
                ("Müşteri", project.get("musteri", "")),
                ("Ülke", project.get("ulke", "")),
                ("Aşama", labels.get(project.get("durum", ""), project.get("durum", ""))),
                ("Tedarikçi", project.get("tedarikci", "")),
                ("Montaj Tipi", project.get("montaj_tipi", "")),
                ("Para Birimi", cur),
                ("Proje Tarihi", _tr_date(project.get("proje_tarihi"))),
                ("Üretim Termini", _tr_date(project.get("termin_tarihi"))),
                ("Müşteri Onayı", _tr_date(project.get("musteri_onay_tarihi"))),
                ("Tedarikçi Onayı", _tr_date(project.get("tedarikci_onay_tarihi"))),
                ("Sevk Tarihi", _tr_date(project.get("sevk_tarihi"))),
                ("Lojistik Firması", project.get("lojistik_firmasi", "")),
                ("Rezervasyon Kodu", project.get("rezervasyon_kodu", "")),
                ("Konteyner / Araç", project.get("konteyner_no", "")),
                ("Gümrük Müşavirliği", project.get("gumruk_musavirligi", "")),
                ("Beyanname No", project.get("beyanname_no", "")),
                ("Not", project.get("notlar", "")),
            ],
            body,
            small,
        ),
        Spacer(1, 5 * mm),
    ]

    # Kalemler
    rows = [
        [
            Paragraph("<b>Ürün</b>", small),
            Paragraph("<b>Adet</b>", small),
            Paragraph("<b>Ölçü (mm)</b>", small),
            Paragraph("<b>Renk / Cam / Kumaş</b>", small),
            Paragraph("<b>Tedarikçi</b>", small),
            Paragraph("<b>Tutar</b>", small),
        ]
    ]
    for i in items:
        detay = " · ".join(
            x
            for x in (
                i.get("yapi_rengi"),
                i.get("panel_rengi"),
                i.get("cam_kombinasyonu"),
                i.get("cam_rengi"),
                i.get("zip_kumasi"),
                i.get("pergola_kumasi"),
                i.get("aydinlatma"),
            )
            if x
        )
        tutar = float(i.get("birim_fiyat") or 0) * float(i.get("adet") or 0)
        rows.append(
            [
                Paragraph(i.get("urun", ""), body),
                Paragraph(str(i.get("adet", 0)), body),
                Paragraph(f"{i.get('genislik_mm', 0)} x {i.get('acilim_mm', 0)}", body),
                Paragraph(detay or "-", small),
                Paragraph(i.get("tedarikci", "") or "-", small),
                Paragraph(_money(tutar, cur) if finans else "-", body),
            ]
        )
    items_table = Table(rows, colWidths=[42 * mm, 12 * mm, 26 * mm, 56 * mm, 24 * mm, 22 * mm])
    items_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("GRID", (0, 0), (-1, -1), 0.25, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    flow += [
        _section(f"ÜRÜN KALEMLERİ ({len(items)})", head),
        Spacer(1, 1.5 * mm),
        items_table if items else Paragraph("Kalem kaydı yok.", small),
        Spacer(1, 5 * mm),
    ]

    # Muhasebe
    if finans:
        flow += [
            _section("MUHASEBE", head),
            Spacer(1, 1.5 * mm),
            _kv_table(
                [
                    ("Satış", _money(muh.get("satis", 0), cur)),
                    ("Alış", _money(muh.get("alis", 0), cur)),
                    ("İskonto", _money(muh.get("iskonto_tutari", 0), cur)),
                    ("Transfer Ücreti", _money(muh.get("transfer_ucreti", 0), cur)),
                    (
                        "Transfer Dahil Toplam Satış",
                        _money(muh.get("transfer_dahil_toplam_satis", 0), cur),
                    ),
                    ("Net Kar", _money(muh.get("net_kar", 0), cur)),
                    ("Kar %", f"{muh.get('kar_yuzdesi', 0)} %"),
                    ("Ödeme Durumu", muh.get("odeme_durumu", "")),
                    ("Toplam Tahsilat", _money(muh.get("toplam_tahsilat", 0), cur)),
                    ("Kalan Bakiye", _money(muh.get("kalan_bakiye", 0), cur)),
                ],
                body,
                small,
            ),
            Spacer(1, 5 * mm),
        ]

    # Sandıklar
    if crates:
        crate_rows = [
            [
                Paragraph("<b>Sandık</b>", small),
                Paragraph("<b>Tedarikçi</b>", small),
                Paragraph("<b>Ölçü (cm)</b>", small),
                Paragraph("<b>Brüt (kg)</b>", small),
                Paragraph("<b>İçerik</b>", small),
            ]
        ]
        for c in crates:
            crate_rows.append(
                [
                    Paragraph(c.get("sandik_no", ""), body),
                    Paragraph(c.get("tedarikci", "") or "-", small),
                    Paragraph(
                        f"{c.get('taban_cm', 0)} x {c.get('uzunluk_cm', 0)} x {c.get('yukseklik_cm', 0)}",
                        body,
                    ),
                    Paragraph(str(c.get("brut_kg", 0)), body),
                    Paragraph(c.get("icerik", "") or "-", small),
                ]
            )
        crate_table = Table(crate_rows, colWidths=[24 * mm, 30 * mm, 38 * mm, 22 * mm, 68 * mm])
        crate_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.25, LINE),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        flow += [
            KeepTogether(
                [_section(f"SANDIK / PAKETLEME ({len(crates)})", head), Spacer(1, 1.5 * mm), crate_table]
            ),
            Spacer(1, 5 * mm),
        ]

    # Revizyonlar
    if revisions:
        rev_rows = [
            [
                Paragraph("<b>Versiyon</b>", small),
                Paragraph("<b>Tarih</b>", small),
                Paragraph("<b>Kaynak</b>", small),
                Paragraph("<b>Açıklama</b>", small),
            ]
        ]
        for r in revisions:
            rev_rows.append(
                [
                    Paragraph(f"V{r.get('versiyon', '')}", body),
                    Paragraph(_tr_date(str(r.get("tarih", ""))[:10]), body),
                    Paragraph(r.get("kaynak", ""), small),
                    Paragraph(r.get("aciklama", "") or "-", small),
                ]
            )
        rev_table = Table(rev_rows, colWidths=[20 * mm, 26 * mm, 22 * mm, 114 * mm])
        rev_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.25, LINE),
                ]
            )
        )
        flow += [
            KeepTogether(
                [_section(f"REVİZYON GEÇMİŞİ ({len(revisions)})", head), Spacer(1, 1.5 * mm), rev_table]
            ),
            Spacer(1, 5 * mm),
        ]

    # Evrak listesi
    if docs:
        doc_rows = [
            [
                Paragraph("<b>Dosya</b>", small),
                Paragraph("<b>Kategori</b>", small),
                Paragraph("<b>Boyut</b>", small),
                Paragraph("<b>Açıklama</b>", small),
            ]
        ]
        for d in docs:
            doc_rows.append(
                [
                    Paragraph(d.get("dosya_adi", ""), body),
                    Paragraph(d.get("kategori", ""), small),
                    Paragraph(f"{(d.get('boyut', 0) / 1024):.0f} KB", small),
                    Paragraph(d.get("aciklama", "") or "-", small),
                ]
            )
        doc_table = Table(doc_rows, colWidths=[64 * mm, 28 * mm, 20 * mm, 70 * mm])
        doc_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.25, LINE),
                ]
            )
        )
        flow += [
            KeepTogether(
                [_section(f"EVRAKLAR ({len(docs)})", head), Spacer(1, 1.5 * mm), doc_table]
            )
        ]

    doc.build(flow)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="proje-{project.get("proje_kodu", "")}.pdf"'
        },
    )
