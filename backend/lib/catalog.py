"""Dinamik tanım listeleri (katalog): süreç aşamaları, ürünler, renkler, kumaşlar, tedarikçiler…

Aşamalar artık sabit kod değil — `catalogs` koleksiyonundan okunur. Kodda kalan
`models.schemas.STAGES` yalnızca ilk kurulum için varsayılan tohumdur.
"""

import re
import unicodedata

from lib.db import db
from models.schemas import STAGE_LABELS, STAGES

CATALOG_TYPES: dict[str, str] = {
    "asama": "Süreç Aşaması",
    "urun": "Ürün",
    "yapi_rengi": "Yapı Rengi",
    "panel_rengi": "Panel Rengi",
    "cam_kombinasyonu": "Cam Kombinasyonu",
    "cam_rengi": "Cam Rengi",
    "kumas": "Kumaş (Zip / Pergola)",
    "aydinlatma": "Aydınlatma",
    "montaj_tipi": "Montaj Tipi",
    "firma": "Firma / Bayi",
    "musteri": "Müşteri",
    "tedarikci": "Tedarikçi",
    "lojistik_firmasi": "Lojistik Firması",
    "para_birimi": "Para Birimi",
    "fatura_tipi": "Fatura Tipi",
}

# Silme koruması: bir tanım bu alanlardan birinde kullanılıyorsa silinemez.
USAGE: dict[str, list[tuple[str, str]]] = {
    "asama": [("projects", "durum")],
    "urun": [("project_items", "urun")],
    "yapi_rengi": [("project_items", "yapi_rengi"), ("project_items", "zip_yapi_rengi")],
    "panel_rengi": [("project_items", "panel_rengi")],
    "cam_kombinasyonu": [("project_items", "cam_kombinasyonu")],
    "cam_rengi": [("project_items", "cam_rengi")],
    "kumas": [("project_items", "zip_kumasi"), ("project_items", "pergola_kumasi")],
    "aydinlatma": [("project_items", "aydinlatma")],
    "montaj_tipi": [("projects", "montaj_tipi")],
    "firma": [("projects", "firma")],
    "musteri": [("projects", "musteri")],
    "tedarikci": [
        ("projects", "tedarikci"),
        ("project_items", "tedarikci"),
        ("project_crates", "tedarikci"),
    ],
    "lojistik_firmasi": [("projects", "lojistik_firmasi")],
    "para_birimi": [("projects", "para_birimi")],
    "fatura_tipi": [("projects", "muhasebe.fatura_tipi")],
}

DEFAULTS: dict[str, list[str]] = {
    "urun": [
        "SKYCLOUD PRIME BIOCLIMATIC SYSTEM",
        "SKYCLOUD MAXI BIOCLIMATIC SYSTEM",
        "SKYCLOUD TREND ACTIVE BIOCLIMATIC SYSTEM",
        "SKYFREE PURE GLASS BIOCLIMATIC SYSTEM",
        "SKYFREE ACTIVE BIOCLIMATIC SYSTEM",
        "SKYFREE MIX GLASS BIOCLIMATIC SYSTEM",
        "SKYNET / FLAT PERGOLA BIOCLIMATIC SYSTEM",
        "SKYFIX PRIME PLUS (WITH POLYCARBONATE)",
        "SKYFIX ACTIVE LAMINATED WITH LAMINE GLASS",
        "SKYFIX ACTIVE DOUBLE (WITH DOUBLE GLAZE)",
        "SKYFIX ACTIVE COMFORT (WITH COMFORT GLAZE)",
        "CUBE ACTIVE LAMINATED WITH LAMINE GLASS",
        "CUBE ACTIVE DOUBLE (WITH DOUBLE GLAZE)",
        "CUBE ACTIVE COMFORT (WITH COMFORT GLAZE)",
        "CUBE PRIME POLYCARBON (WITH POLYCARBONATE)",
        "CEDRUS SILVER CLASSIC PERGOLA SYSTEM",
        "CEDRUS GOLD CLASSIC PERGOLA SYSTEM",
        "CEDRUS DIAMOND CLASSIC PERGOLA SYSTEM",
        "JUNIPER SILVER CLASSIC PERGOLA SYSTEM",
        "JUNIPER GOLD CLASSIC PERGOLA SYSTEM",
        "JUNIPER DIAMOND CLASSIC PERGOLA SYSTEM",
        "PINO SILVER CLASSIC PERGOLA SYSTEM",
        "PINO GOLD CLASSIC PERGOLA SYSTEM",
        "PINO DIAMOND CLASSIC PERGOLA SYSTEM",
        "SELVI GOLD CLASSIC PERGOLA SYSTEM",
        "SELVI DIAMOND CLASSIC PERGOLA SYSTEM",
        "SEKOYA SILVER CLASSIC PERGOLA SYSTEM",
        "SEKOYA GOLD CLASSIC PERGOLA SYSTEM",
        "BOSSO GOLD CLASSIC PERGOLA SYSTEM",
        "BOSSO DIAMOND CLASSIC PERGOLA SYSTEM",
        "DAPHNE SILVER CLASSIC PERGOLA SYSTEM",
        "DAPHNE DIAMOND CLASSIC PERGOLA SYSTEM",
        "OLIVA SILVER CLASSIC PERGOLA SYSTEM",
        "OLIVA DIAMOND CLASSIC PERGOLA SYSTEM",
        "CARPE SILVER CLASSIC PERGOLA SYSTEM",
        "CARPE GOLD CLASSIC PERGOLA SYSTEM",
        "CARPE DIAMOND CLASSIC PERGOLA SYSTEM",
        "WILLOW SILVER CLASSIC PERGOLA SYSTEM",
        "WILLOW GOLD CLASSIC PERGOLA SYSTEM",
        "OXIA DIAMOND CLASSIC PERGOLA SYSTEM",
        "VERLASS ALBATRO ACTIVE GUILLOTINE SYSTEM",
        "VERLASS ALBATRO ECO WITHOUT MOTOR GUILLOTINE SYSTEM",
        "VERLASS CORMORANO ACTIVE GUILLOTINE SYSTEM",
        "VERLASS CORMORANO ECO WITHOUT MOTOR GUILLOTINE SYSTEM",
        "BORA 8MM SLIDING GLASS SYSTEM",
        "BORA 10MM SLIDING GLASS SYSTEM",
        "BORA 18MM SLIDING GLASS SYSTEM",
        "BORA FIX 8MM FIXED GLASS SYSTEM",
        "BORA FIX 10MM FIXED GLASS SYSTEM",
        "BORA FIX 18MM FIXED GLASS SYSTEM",
        "BORA FIX 10MM TRIANGLE FIXED GLASS SYSTEM",
        "PIER 10MM SLIDING GLASS SYSTEM (WITHOUT FRAME)",
        "C60 FIX 8MM FIXED GLASS SYSTEM",
        "C60 FIX 10MM FIXED GLASS SYSTEM",
        "C60 FIX 20MM FIXED GLASS SYSTEM",
        "ISCB140 SLIDING GLASS SYSTEM",
        "SUNDOOR 8MM SINGLE DOOR",
        "SUNDOOR 10MM SINGLE DOOR",
        "SUNDOOR 20MM SINGLE DOOR",
        "SUNMASTER PRIME FIBER ZIP SYSTEM",
        "SUNMASTER ACTIVE FIBER ZIP SYSTEM",
        "SUNMASTER PRIME PVC ZIP SYSTEM",
        "SUNMASTER PRIME USA-FIBER ZIP SYSTEM",
        "SUNMASTER ACTIVE USA-FIBER ZIP SYSTEM",
        "SUNMASTER ROOF ZIP SYSTEM",
        "WG70 WINTER GARDEN",
        "WD64 SINGLE DOOR",
        "WD64 DOUBLE DOOR",
        "WD64 FIXED JOINERY",
        "WD64 TRIANGLE FIXED JOINERY",
        "FD60 BIFOLD DOOR",
        "SOMFY MOTOR",
        "MOTOR ALTUS 60 RTS 120/12 VVF 3M",
        "SOMFY WIND SENSOR EOLIS IO / BATTERY OPERATED",
        "TELECO WIND SENSOR RTS",
        "LED STRIP",
        "ZENİT LED SİSTEM",
        "STEEL CONS. 50x150x3 MM",
        "STEEL CONS. 150x150x3 MM",
        "COMPOSITE PANEL",
        "SPRAY PAINT",
        "YEDEK PARÇA",
    ],
    "yapi_rengi": [
        "SP-7016 ANTHRACITE GREY FSM",
        "SP-9005 FSM",
        "SP-9007 GREY ALUMINIUM",
        "SP-9001 CREAM GLOSS",
        "SP-8019 GREY BROWN FSM",
        "SP-1036 FSM",
        "SI-8860 FSM",
        "SI-7811 FSM",
        "SI-7046 TELEGRAY GLOSS",
        "SI-6013 FSM",
        "SI-6209 FSM",
        "SI-5987 FSM",
        "SI-9006 FSM",
        "SJ-8100 BROWN FSM",
        "SJ-7100 FSM",
        "SN-9403 C44",
        "SN-93028 A 59",
        "RAL 9016 TEXTURE",
        "ŞEFFAF",
        "SİYAH",
        "YEŞİL",
        "GREY",
    ],
    "panel_rengi": [
        "GREY 8100 - BASIC",
        "WHITE 8200 - BASIC",
        "CREAM 8300 - BASIC",
        "GREY 3030 - 3D",
        "METALLIC 4040 - 3D",
        "CLARED RED 6060 - 3D",
        "BLACK 7070 - 3D",
        "DARK GREY 9090 - 3D",
        "ECO GREY 3D",
    ],
    "cam_kombinasyonu": [
        "8MM TEMPERLİ",
        "10MM TEMPERLİ",
        "18MM LAMİNE",
        "20MM LAMİNE",
        "4MM TEMPER + 12HB + 4MM TEMPERLİ ISICAM",
        "5MM TEMPER + 12HB + 5MM TEMPERLİ ISICAM",
        "6MM TEMPER + 12HB + 6MM KONFOR CAM",
        "POLİKARBON",
    ],
    "cam_rengi": ["ŞEFFAF", "FÜME", "BRONZ", "REFLEKTE", "YEŞİL", "SET IN STONE"],
    "kumas": [
        "RECASENS R-000",
        "RECASENS R-400",
        "SERGE FERRARI 86-2044",
        "SERGE FERRARI 96-2171",
        "SERGE FERRARI 96-2047",
        "PERGOLA KUMAŞ",
        "WHITE SUNSET",
        "COOL WHITE",
    ],
    "aydinlatma": [
        "AYDINLATMASIZ",
        "LED STRIP",
        "LED SPOT",
        "ZENİT LED SİSTEM",
        "RGB ÇEVRE AYDINLATMA",
        "TELECO/SOMFY LIGHT RECEIVER RTS",
    ],
    "montaj_tipi": ["DUVARA MONTAJ", "SERBEST AYAKLI", "ANKASTRE", "KÖŞE MONTAJ"],
    "firma": [
        "PRO ALU SYSTEMES",
        "ZANZASOL SNC DI TOUKAMI OMAR & C",
        "LA TENDAMANIA S.R.L.",
        "EKSTERIER (ARH TRADICIJA d.o.o.)",
        "TROPICANA STORES",
        "ALLUMONDO A.Ş.",
        "COVERTURE SAS",
        "ENNTRIS d.o.o.",
        "ESTERNI DESIGN SRL",
        "EUROTENDA F.D. GROUP S.R.L.S.",
        "HOME LAB PARMA - TECNICO OUTDOOR",
        "INTERLANDI SRL",
        "ALLPAINT S.R.L.",
        "PERGOLA VALLEY LLC",
        "SEIEFFE SRL",
        "TENTE DEKORASYON SAN. VE TİC. A.Ş.",
        "TECNOMBRA - ANGELS SRL - VISFLEX",
        "TECNOTENDA",
        "TENDE FAZZONE TF SRL",
        "VERDE PROFILO",
        "AZUR ALU",
        "JPA MENUISERIES",
        "GBS ADVANCED CONSTRUCTION CORP.",
        "GLOBALFENSTER GMBH",
        "MODUS DEHORS SRL",
        "SUNSTORE SONNENSCHUTZTECHNIK GMBH",
        "TENDENZE D'ARREDO",
        "ARC EN CIEL",
        "SA LEMOINE STORE DECO SARL",
        "STORES & FERMETURES",
        "ISOL ECO",
        "PRATOTENDE",
        "ARTBEY",
        "NATURA YAPI ALÜMİNYUM VE CAM SAN. TİC. LTD. ŞTİ.",
    ],
    "musteri": [
        "711 HOTEL",
        "ORCHARD",
        "321W 38ST",
        "PROJECT GIL",
        "CEM",
        "ANTON",
        "MORASCHINI",
        "DANIEL SAVIO",
        "STEFANIA MORETTI",
        "MARKO JURKAS",
        "GROBELNIK",
        "HOUSE HRIBAR",
        "APP. KRISTIAN B47",
        "APP. JANSA PARTS",
        "STEVEN WASHIO",
        "DAVID SHOULTZ",
        "AVLI RIVER PREMIUM PERGOLA",
        "PAYET OLIVIER",
        "SENOZETNIK",
        "PREMIUM PERGOLA",
    ],
    "tedarikci": [
        "MERLOT PERGOLA ALÜMİNYUM TEKSTİL SAN. VE TİC. LTD. ŞTİ.",
        "TENTE DEKORASYON SAN. VE TİC. A.Ş.",
        "TON ALUMİNYUM",
        "ALTAY ALUMİNYUM",
        "SUN ALUMİNYUM",
        "ERG DIZAYN",
        "ALLPAINT S.R.L.",
        "KOÇTAŞ ELEKTRONİK",
        "TAMTEL KABLO",
        "OKTAY KLEMENS",
        "ARAT MOTOR KURYE",
        "ATÖLYE (KENDİ ÜRETİM)",
    ],
    "lojistik_firmasi": [
        "MEDYA LOJİSTİK",
        "EKOL LOJİSTİK",
        "DSV ROAD",
        "MARS LOJİSTİK",
        "ALIŞAN LOJİSTİK",
        "ARAT MOTOR KURYE",
        "KENDİ ARACIMIZ",
    ],
    "para_birimi": ["EUR", "USD", "TRY", "GBP"],
}

FATURA_DEFAULTS = [
    ("ihrac_kayitli", "İhraç Kayıtlı"),
    ("kdvli", "KDV'li"),
    ("kdv_muaf", "KDV Muaf"),
]

# Aşama rozet renkleri — sıraya göre döner, yeni aşama eklendiğinde de bir ton alır.
STAGE_TONES = [
    "sky",
    "blue",
    "amber",
    "emerald",
    "indigo",
    "yellow",
    "orange",
    "cyan",
    "teal",
    "purple",
    "green",
]


def slugify(text: str) -> str:
    """'Müşteri Onayı' → 'musteri_onayi' — aşama anahtarı üretir."""
    normalized = unicodedata.normalize("NFKD", text.replace("ı", "i").replace("İ", "i"))
    ascii_text = normalized.encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_")
    return slug or "tanim"


async def list_catalog(tip: str, sadece_aktif: bool = True) -> list[dict]:
    query: dict = {"tip": tip}
    if sadece_aktif:
        query["aktif"] = True
    return await db.catalogs.find(query).sort("sira", 1).to_list(500)


async def stage_keys() -> list[str]:
    rows = await list_catalog("asama")
    return [r["deger"] for r in rows] or list(STAGES)


async def stage_labels() -> dict[str, str]:
    rows = await list_catalog("asama", sadece_aktif=False)
    return {r["deger"]: r["label"] for r in rows} or dict(STAGE_LABELS)


async def ensure_catalog_defaults() -> None:
    """İlk açılışta tanım listelerini tohumlar; var olanlara dokunmaz."""
    import uuid

    async def seed(tip: str, pairs: list[tuple[str, str]]) -> None:
        """Eksik olan varsayılanları ekler; var olan kayıtlara ve sıralamaya dokunmaz."""
        mevcut = {r["deger"] for r in await db.catalogs.find({"tip": tip}).to_list(1000)}
        son = await db.catalogs.find({"tip": tip}).sort("sira", -1).to_list(1)
        sira = (son[0]["sira"] + 1) if son else 0
        yeni = []
        for deger, label in pairs:
            if deger in mevcut:
                continue
            yeni.append(
                {
                    "id": str(uuid.uuid4()),
                    "tip": tip,
                    "deger": deger,
                    "label": label,
                    "sira": sira,
                    "aktif": True,
                    "sistem": tip == "asama",
                }
            )
            sira += 1
        if yeni:
            await db.catalogs.insert_many(yeni)

    await seed("asama", [(s, STAGE_LABELS[s]) for s in STAGES])
    await seed("fatura_tipi", FATURA_DEFAULTS)
    for tip, values in DEFAULTS.items():
        await seed(tip, [(v, v) for v in values])
