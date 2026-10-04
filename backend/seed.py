"""Idempotent seed data: demo team user + realistic export projects across the 11 stages.

Run: cd /app/backend && python seed.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from lib.auth import hash_password
from lib.db import db, ensure_indexes
from models.schemas import (
    Activity,
    Muhasebe,
    Odeme,
    Project,
    ProjectCrate,
    ProjectItem,
    compute_cbm,
    compute_muhasebe,
)

TODAY = datetime.now(timezone.utc).date()


def d(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


USERS = [
    ("admin@pergola.com", "pergola123", "Ahmet Yılmaz"),
    ("ekip@pergola.com", "pergola123", "Elif Demir"),
]

PROJECTS = [
    {
        "firma": "Pergola Systems GmbH",
        "musteri": "Klaus Berger",
        "ulke": "Almanya",
        "proje_adi": "Münih Restoran Terası — Bioklimatik Pergola",
        "tedarikci": "ASAŞ Alüminyum",
        "durum": "uretim",
        "montaj_tipi": "Duvara Montaj",
        "para_birimi": "EUR",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-24),
        "musteri_onay_tarihi": d(-18),
        "tedarikci_onay_tarihi": d(-16),
        "termin_tarihi": d(6),
        "lojistik_firmasi": "Ekol Lojistik",
        "notlar": "Motor Somfy olacak, rüzgâr sensörü dahil.",
        "muhasebe": {"satis": 42500, "alis": 28700, "iskonto_tutari": 1500, "transfer_ucreti": 2400, "odemeler": [12000, 10000, 0, 0, 0]},
        "kalemler": [
            {"urun": "Bioklimatik Pergola (Alüminyum Lamelli)", "adet": 2, "genislik_mm": 6000, "acilim_mm": 4000, "yapi_rengi": "RAL 7016 Antrasit Gri", "panel_rengi": "RAL 7016", "aydinlatma": "Entegre LED Dimmerli", "aydinlatma_rengi": "3000K", "led_strip_mtul": 18, "led_spot_adet": 8, "tedarikci": "ASAŞ Alüminyum", "birim_fiyat": 12400},
            {"urun": "Zip Perde / Dış Cephe", "adet": 3, "genislik_mm": 4000, "acilim_mm": 2800, "zip_yapi_rengi": "RAL 7016", "zip_kumasi": "Serge Ferrari Soltis 86", "tedarikci": "Tente Pro", "birim_fiyat": 2100},
        ],
        "sandiklar": [
            {"sandik_no": "SND-01", "icerik": "Taşıyıcı dikmeler ve kiriş profilleri", "taban_cm": 120, "uzunluk_cm": 620, "yukseklik_cm": 45, "adet": 1, "brut_kg": 680, "tedarikci": "ASAŞ Alüminyum"},
            {"sandik_no": "SND-02", "icerik": "Alüminyum lameller + motor kiti", "taban_cm": 110, "uzunluk_cm": 420, "yukseklik_cm": 60, "adet": 1, "brut_kg": 540, "tedarikci": "ASAŞ Alüminyum"},
        ],
    },
    {
        "firma": "Solaris Outdoor SARL",
        "musteri": "Marie Lefevre",
        "ulke": "Fransa",
        "proje_adi": "Nice Villa — Giyotin Cam Sistemi",
        "tedarikci": "Şişecam Bayi",
        "durum": "lojistik_rezervasyon",
        "montaj_tipi": "Serbest Ayaklı",
        "para_birimi": "EUR",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-40),
        "musteri_onay_tarihi": d(-33),
        "tedarikci_onay_tarihi": d(-30),
        "termin_tarihi": d(-4),
        "sevk_tarihi": d(3),
        "lojistik_firmasi": "DSV Road",
        "rezervasyon_kodu": "DSV-884213",
        "notlar": "Rezervasyon onaylandı, yükleme için tır bekleniyor.",
        "muhasebe": {"satis": 68900, "alis": 46200, "iskonto_tutari": 2900, "transfer_ucreti": 3800, "odemeler": [20000, 20000, 15000, 0, 0]},
        "kalemler": [
            {"urun": "Giyotin Cam Sistemi (Motorlu)", "adet": 4, "genislik_mm": 3200, "acilim_mm": 2600, "yapi_rengi": "RAL 9005 Mat Siyah", "cam_olcusu": "3200x2600", "cam_rengi": "Füme", "cam_kombinasyonu": "5+12+5 Solar Low-E Temperli", "tedarikci": "Şişecam Bayi", "birim_fiyat": 11800},
        ],
        "sandiklar": [
            {"sandik_no": "SND-01", "icerik": "Giyotin cam kasa profilleri", "taban_cm": 100, "uzunluk_cm": 340, "yukseklik_cm": 70, "adet": 2, "brut_kg": 910, "tedarikci": "Şişecam Bayi"},
        ],
    },
    {
        "firma": "Emirates Shade LLC",
        "musteri": "Omar Al Rashid",
        "ulke": "BAE",
        "proje_adi": "Dubai Marina Çatı Terası — Sürme Cam",
        "tedarikci": "Cam Teknik",
        "durum": "teklif_proforma",
        "montaj_tipi": "Duvara Montaj",
        "para_birimi": "USD",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-6),
        "termin_tarihi": d(34),
        "notlar": "Proforma gönderildi, bayi fiyat revizyonu istiyor.",
        "muhasebe": {"satis": 54000, "alis": 35500, "iskonto_tutari": 0, "transfer_ucreti": 5200, "odemeler": [0, 0, 0, 0, 0]},
        "kalemler": [
            {"urun": "Sürme Cam Sistemi (5 Raylı)", "adet": 6, "genislik_mm": 5000, "acilim_mm": 2400, "yapi_rengi": "RAL 9016 Beyaz", "cam_olcusu": "5000x2400", "cam_kombinasyonu": "10mm Temperli Şeffaf", "tedarikci": "Cam Teknik", "birim_fiyat": 7900},
        ],
        "sandiklar": [],
    },
    {
        "firma": "Dutch Garden Living BV",
        "musteri": "Sven de Vries",
        "ulke": "Hollanda",
        "proje_adi": "Rotterdam Cafe — Montaja Hazır Pergola",
        "tedarikci": "Tente Pro",
        "durum": "yuklendi_sevk",
        "montaj_tipi": "Serbest Ayaklı",
        "para_birimi": "EUR",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-58),
        "musteri_onay_tarihi": d(-50),
        "tedarikci_onay_tarihi": d(-47),
        "sevk_tarihi": d(-2),
        "lojistik_firmasi": "Mars Lojistik",
        "rezervasyon_kodu": "MRS-55120",
        "konteyner_no": "MSCU-7781234",
        "notlar": "Konteyner çıkışı yapıldı, konşimento bekleniyor.",
        "muhasebe": {"satis": 31200, "alis": 19800, "iskonto_tutari": 800, "transfer_ucreti": 2100, "odemeler": [15000, 10000, 5400, 0, 0]},
        "kalemler": [
            {"urun": "Montaja Hazır Pergola (PVC Kumaşlı)", "adet": 3, "genislik_mm": 4500, "acilim_mm": 3500, "yapi_rengi": "RAL 8019 Kahve Dokulu", "pergola_kumasi": "Sattler PVC Blackout 850 gr", "kumas_profil_rengi": "RAL 8019", "aydinlatma": "RGB Çevre Aydınlatma", "led_strip_mtul": 24, "tedarikci": "Tente Pro", "birim_fiyat": 8600},
        ],
        "sandiklar": [
            {"sandik_no": "SND-01", "icerik": "Pergola profilleri", "taban_cm": 90, "uzunluk_cm": 470, "yukseklik_cm": 50, "adet": 3, "brut_kg": 1240, "tedarikci": "Tente Pro"},
        ],
    },
    {
        "firma": "Anadolu Yapı A.Ş.",
        "musteri": "Burak Kaya",
        "ulke": "Türkiye",
        "proje_adi": "Bodrum Otel Havuz Başı — Bioklimatik",
        "tedarikci": "ASAŞ Alüminyum",
        "durum": "musteri_onayi",
        "montaj_tipi": "Serbest Ayaklı",
        "para_birimi": "TRY",
        "satis_tipi": "yurtici",
        "proje_tarihi": d(-11),
        "musteri_onay_tarihi": d(-1),
        "termin_tarihi": d(28),
        "notlar": "KDV'li fatura kesilecek, yurtiçi montaj ekibimiz yapacak.",
        "muhasebe": {"satis": 1850000, "alis": 1210000, "iskonto_tutari": 50000, "transfer_ucreti": 35000, "fatura_tipi": "kdvli", "odemeler": [600000, 0, 0, 0, 0]},
        "kalemler": [
            {"urun": "Bioklimatik Pergola (Alüminyum Lamelli)", "adet": 5, "genislik_mm": 7000, "acilim_mm": 4500, "yapi_rengi": "RAL 9006 Metalik Gümüş", "panel_rengi": "RAL 9006", "aydinlatma": "Entegre LED 4000K", "led_spot_adet": 20, "led_strip_mtul": 40, "tedarikci": "ASAŞ Alüminyum", "birim_fiyat": 310000},
        ],
        "sandiklar": [],
    },
    {
        "firma": "Baghdad Modern Living",
        "musteri": "Hassan Jabbar",
        "ulke": "Irak",
        "proje_adi": "Bağdat Rezidans — Zip Perde Paketi",
        "tedarikci": "Tente Pro",
        "durum": "revizyon",
        "montaj_tipi": "Duvara Montaj",
        "para_birimi": "USD",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-9),
        "termin_tarihi": d(40),
        "notlar": "3. revizyon: kumaş rengi ve ölçüler değişti.",
        "muhasebe": {"satis": 23400, "alis": 15100, "iskonto_tutari": 400, "transfer_ucreti": 1800, "odemeler": [0, 0, 0, 0, 0]},
        "kalemler": [
            {"urun": "Zip Perde / Dış Cephe Güneş Kırıcı", "adet": 12, "genislik_mm": 3000, "acilim_mm": 3200, "zip_yapi_rengi": "RAL 9016", "zip_kumasi": "Dickson Sunworker Mat", "tedarikci": "Tente Pro", "birim_fiyat": 1850},
        ],
        "sandiklar": [],
    },
    {
        "firma": "British Veranda Ltd",
        "musteri": "James Holloway",
        "ulke": "İngiltere",
        "proje_adi": "Manchester Veranda — Sürme Cam + Pergola",
        "tedarikci": "Cam Teknik",
        "durum": "paketleme",
        "montaj_tipi": "Duvara Montaj",
        "para_birimi": "EUR",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-35),
        "musteri_onay_tarihi": d(-28),
        "tedarikci_onay_tarihi": d(-26),
        "termin_tarihi": d(1),
        "notlar": "Sandık listesi firmadan geldi, ölçüler girildi.",
        "muhasebe": {"satis": 47600, "alis": 30400, "iskonto_tutari": 1200, "transfer_ucreti": 2950, "odemeler": [20000, 12000, 0, 0, 0]},
        "kalemler": [
            {"urun": "Sürme Cam Sistemi (3 Raylı)", "adet": 4, "genislik_mm": 4200, "acilim_mm": 2300, "yapi_rengi": "RAL 7016 Antrasit Gri", "cam_kombinasyonu": "8mm Temperli Şeffaf", "cam_rengi": "Şeffaf", "tedarikci": "Cam Teknik", "birim_fiyat": 6900},
            {"urun": "Montaja Hazır Pergola (PVC Kumaşlı)", "adet": 2, "genislik_mm": 5000, "acilim_mm": 3600, "pergola_kumasi": "Sattler PVC Blackout 850 gr", "yapi_rengi": "RAL 7016", "tedarikci": "Tente Pro", "birim_fiyat": 9200},
        ],
        "sandiklar": [
            {"sandik_no": "SND-01", "icerik": "Sürme cam kasaları", "taban_cm": 95, "uzunluk_cm": 440, "yukseklik_cm": 55, "adet": 2, "brut_kg": 760, "tedarikci": "Cam Teknik"},
            {"sandik_no": "SND-02", "icerik": "Pergola profil ve kumaş rulosu", "taban_cm": 80, "uzunluk_cm": 520, "yukseklik_cm": 40, "adet": 1, "brut_kg": 410, "tedarikci": "Tente Pro"},
        ],
    },
    {
        "firma": "Alpine Shade AG",
        "musteri": "Lukas Meier",
        "ulke": "Avusturya",
        "proje_adi": "Innsbruck Şalet — Kış Bahçesi",
        "tedarikci": "Şişecam Bayi",
        "durum": "gumruk_beyanname",
        "montaj_tipi": "Duvara Montaj",
        "para_birimi": "EUR",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-72),
        "musteri_onay_tarihi": d(-64),
        "tedarikci_onay_tarihi": d(-61),
        "sevk_tarihi": d(-6),
        "lojistik_firmasi": "Alışan Lojistik",
        "rezervasyon_kodu": "ALS-10233",
        "konteyner_no": "34 PRG 118",
        "gumruk_musavirligi": "Ege Gümrükleme",
        "beyanname_no": "26341200EX004512",
        "notlar": "İhraç kayıtlı fatura kesildi, beyanname tescil edildi.",
        "muhasebe": {"satis": 89300, "alis": 58900, "iskonto_tutari": 3300, "transfer_ucreti": 4600, "odemeler": [30000, 30000, 26000, 0, 0]},
        "kalemler": [
            {"urun": "Sabit Cam Tavan & Kış Bahçesi", "adet": 1, "genislik_mm": 9000, "acilim_mm": 5000, "yapi_rengi": "RAL 9005 Mat Siyah", "cam_kombinasyonu": "6+12+6 Konfor Cam", "cam_rengi": "Reflekte Bronz", "tedarikci": "Şişecam Bayi", "birim_fiyat": 61000},
        ],
        "sandiklar": [
            {"sandik_no": "SND-01", "icerik": "Cam tavan taşıyıcı sistemi", "taban_cm": 130, "uzunluk_cm": 910, "yukseklik_cm": 60, "adet": 1, "brut_kg": 1580, "tedarikci": "Şişecam Bayi"},
        ],
    },
    {
        "firma": "Pergola Systems GmbH",
        "musteri": "Klaus Berger",
        "ulke": "Almanya",
        "proje_adi": "Hamburg Ofis Bahçesi — Kasetli Tente",
        "tedarikci": "Tente Pro",
        "durum": "tamamlandi",
        "arsiv": True,
        "montaj_tipi": "Duvara Montaj",
        "para_birimi": "EUR",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-120),
        "musteri_onay_tarihi": d(-112),
        "tedarikci_onay_tarihi": d(-110),
        "sevk_tarihi": d(-70),
        "lojistik_firmasi": "Ekol Lojistik",
        "konteyner_no": "TCLU-5512003",
        "gumruk_musavirligi": "Ege Gümrükleme",
        "beyanname_no": "25341200EX009981",
        "notlar": "Tahsilat kapandı, dosya arşivlendi.",
        "muhasebe": {"satis": 26400, "alis": 16100, "iskonto_tutari": 400, "transfer_ucreti": 1500, "odemeler": [10000, 10000, 6000, 0, 0]},
        "kalemler": [
            {"urun": "Kasetli Tente / Mafsallı Tente", "adet": 4, "genislik_mm": 4000, "acilim_mm": 3000, "yapi_rengi": "RAL 9016 Beyaz", "kumas_profil_rengi": "RAL 9016", "pergola_kumasi": "Dickson Sunworker Mat", "tedarikci": "Tente Pro", "birim_fiyat": 5900},
        ],
        "sandiklar": [],
    },
    {
        "firma": "Ege Mimarlık",
        "musteri": "Seda Arslan",
        "ulke": "Türkiye",
        "proje_adi": "İzmir Kafe — Giyotin Cam",
        "tedarikci": "Cam Teknik",
        "durum": "talep_alindi",
        "montaj_tipi": "Duvara Montaj",
        "para_birimi": "TRY",
        "satis_tipi": "yurtici",
        "proje_tarihi": d(0),
        "notlar": "Ölçü alındı, çizim hazırlanacak.",
        "muhasebe": {"satis": 0, "alis": 0, "odemeler": [0, 0, 0, 0, 0]},
        "kalemler": [],
        "sandiklar": [],
    },
    {
        "firma": "Solaris Outdoor SARL",
        "musteri": "Marie Lefevre",
        "ulke": "Fransa",
        "proje_adi": "Lyon Bistro — Zip Perde Yenileme",
        "tedarikci": "Tente Pro",
        "durum": "fatura",
        "montaj_tipi": "Duvara Montaj",
        "para_birimi": "EUR",
        "satis_tipi": "ihracat",
        "proje_tarihi": d(-52),
        "musteri_onay_tarihi": d(-45),
        "tedarikci_onay_tarihi": d(-43),
        "sevk_tarihi": d(-3),
        "lojistik_firmasi": "DSV Road",
        "rezervasyon_kodu": "DSV-889001",
        "notlar": "Tedarikçi faturası geldi, ihraç kayıtlı fatura kesiliyor.",
        "muhasebe": {"satis": 18700, "alis": 11900, "iskonto_tutari": 0, "transfer_ucreti": 1200, "odemeler": [9000, 0, 0, 0, 0]},
        "kalemler": [
            {"urun": "Zip Perde / Dış Cephe Güneş Kırıcı", "adet": 8, "genislik_mm": 2800, "acilim_mm": 2900, "zip_kumasi": "Serge Ferrari Soltis 86", "zip_yapi_rengi": "RAL 7016", "tedarikci": "Tente Pro", "birim_fiyat": 2050},
        ],
        "sandiklar": [
            {"sandik_no": "SND-01", "icerik": "Zip perde kaset ve kılavuzlar", "taban_cm": 60, "uzunluk_cm": 300, "yukseklik_cm": 40, "adet": 2, "brut_kg": 290, "tedarikci": "Tente Pro"},
        ],
    },
]


async def main() -> None:
    for coll in ("users", "sessions", "projects", "project_items", "project_crates", "activities"):
        await db[coll].delete_many({})
    await ensure_indexes()

    for email, sifre, ad in USERS:
        await db.users.insert_one(
            {
                "id": __import__("uuid").uuid4().hex,
                "email": email,
                "ad_soyad": ad,
                "created_at": datetime.now(timezone.utc),
                "sifre_hash": hash_password(sifre),
            }
        )

    year = TODAY.year
    for idx, p in enumerate(PROJECTS, start=1):
        raw = dict(p)
        kalemler = raw.pop("kalemler", [])
        sandiklar = raw.pop("sandiklar", [])
        mh = raw.pop("muhasebe", {})
        odeme_tutarlari = (mh.pop("odemeler", []) + [0] * 5)[:5]
        muhasebe = compute_muhasebe(
            Muhasebe(
                **mh,
                odemeler=[
                    Odeme(tutar=float(t), tarih=d(-20 + i * 5) if t else None)
                    for i, t in enumerate(odeme_tutarlari)
                ],
            )
        )
        project = Project(proje_kodu=f"PRG-{year}-{idx:03d}", muhasebe=muhasebe, **raw)
        project.kalem_sayisi = len(kalemler)
        await db.projects.insert_one(project.model_dump())

        for k in kalemler:
            await db.project_items.insert_one(ProjectItem(proje_id=project.id, **k).model_dump())
        for c in sandiklar:
            await db.project_crates.insert_one(
                compute_cbm(ProjectCrate(proje_id=project.id, **c)).model_dump()
            )

        await db.activities.insert_one(
            Activity(
                proje_id=project.id,
                proje_kodu=project.proje_kodu,
                tip="olusturma",
                mesaj=f"{project.proje_kodu} projesi oluşturuldu",
                kullanici="Ahmet Yılmaz",
                yeni_durum="talep_alindi",
                gun=project.proje_tarihi,
                created_at=datetime.now(timezone.utc) - timedelta(days=idx, hours=3),
            ).model_dump()
        )
        if project.durum != "talep_alindi":
            await db.activities.insert_one(
                Activity(
                    proje_id=project.id,
                    proje_kodu=project.proje_kodu,
                    tip="asama",
                    mesaj=f"Aşama güncellendi → {project.durum}",
                    kullanici="Elif Demir",
                    eski_durum="talep_alindi",
                    yeni_durum=project.durum,
                    gun=TODAY.isoformat(),
                    created_at=datetime.now(timezone.utc) - timedelta(hours=idx),
                ).model_dump()
            )

    print(f"Seed tamam: {len(PROJECTS)} proje, {len(USERS)} kullanıcı.")


if __name__ == "__main__":
    asyncio.run(main())
