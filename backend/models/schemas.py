"""Pydantic v2 models. Each has a hand-written TS mirror in frontend/src/lib/types.ts."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

STAGES = [
    "talep_alindi",
    "teklif_proforma",
    "revizyon",
    "musteri_onayi",
    "uretim",
    "paketleme",
    "lojistik_rezervasyon",
    "yuklendi_sevk",
    "fatura",
    "gumruk_beyanname",
    "tamamlandi",
]

STAGE_LABELS = {
    "talep_alindi": "Talep Alındı",
    "teklif_proforma": "Teklif / Proforma",
    "revizyon": "Revizyon",
    "musteri_onayi": "Müşteri Onayı",
    "uretim": "Üretim",
    "paketleme": "Paketleme / Sandık",
    "lojistik_rezervasyon": "Lojistik / Rezervasyon",
    "yuklendi_sevk": "Yüklendi / Sevk",
    "fatura": "Fatura",
    "gumruk_beyanname": "Gümrük / Beyanname",
    "tamamlandi": "Tamamlandı",
}


def _uid() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------- auth ----------
class User(BaseModel):
    id: str = Field(default_factory=_uid)
    email: str
    ad_soyad: str
    created_at: datetime = Field(default_factory=now_utc)


class RegisterInput(BaseModel):
    email: EmailStr
    sifre: str = Field(min_length=4)
    ad_soyad: str = Field(min_length=2)


class LoginInput(BaseModel):
    email: EmailStr
    sifre: str


# ---------- accounting ----------
class Odeme(BaseModel):
    tutar: float = 0.0
    tarih: Optional[str] = None
    not_: str = Field(default="", alias="not")

    model_config = {"populate_by_name": True}


class Muhasebe(BaseModel):
    satis: float = 0.0
    alis: float = 0.0
    iskonto_tutari: float = 0.0
    transfer_ucreti: float = 0.0
    fatura_tipi: str = "ihrac_kayitli"  # ihrac_kayitli | kdvli | kdv_muaf
    odeme_durumu: str = "bekliyor"  # bekliyor | kismi | tamamlandi
    odemeler: List[Odeme] = Field(default_factory=lambda: [Odeme() for _ in range(5)])
    # computed, filled by compute_muhasebe()
    transfer_dahil_toplam_satis: float = 0.0
    net_kar: float = 0.0
    kar_yuzdesi: float = 0.0
    toplam_tahsilat: float = 0.0
    kalan_bakiye: float = 0.0


def compute_muhasebe(m: Muhasebe) -> Muhasebe:
    """Derived accounting figures — single source of truth, never computed in the browser."""
    net_satis = m.satis - m.iskonto_tutari
    m.transfer_dahil_toplam_satis = round(net_satis + m.transfer_ucreti, 2)
    m.net_kar = round(net_satis - m.alis - m.transfer_ucreti, 2)
    m.kar_yuzdesi = round((m.net_kar / net_satis * 100), 2) if net_satis else 0.0
    m.toplam_tahsilat = round(sum(o.tutar for o in m.odemeler), 2)
    m.kalan_bakiye = round(net_satis - m.toplam_tahsilat, 2)
    if m.toplam_tahsilat <= 0:
        m.odeme_durumu = "bekliyor"
    elif m.kalan_bakiye > 0.009:
        m.odeme_durumu = "kismi"
    else:
        m.odeme_durumu = "tamamlandi"
    return m


# ---------- projects ----------
class ProjectBase(BaseModel):
    firma: str = ""
    musteri: str = ""
    ulke: str = ""
    proje_tarihi: str = ""  # YYYY-MM-DD
    proje_adi: str = ""
    tedarikci: str = ""
    durum: str = "talep_alindi"
    arsiv: bool = False
    musteri_onay_tarihi: Optional[str] = None
    tedarikci_onay_tarihi: Optional[str] = None
    sevk_tarihi: Optional[str] = None
    termin_tarihi: Optional[str] = None
    montaj_tipi: str = ""
    para_birimi: str = "EUR"
    satis_tipi: str = "ihracat"  # ihracat | yurtici
    lojistik_firmasi: str = ""
    rezervasyon_kodu: str = ""
    konteyner_no: str = ""
    gumruk_musavirligi: str = ""
    beyanname_no: str = ""
    notlar: str = ""


class ProjectCreate(ProjectBase):
    proje_kodu: Optional[str] = None


class ProjectUpdate(ProjectBase):
    pass


class Project(ProjectBase):
    id: str = Field(default_factory=_uid)
    proje_kodu: str
    muhasebe: Muhasebe = Field(default_factory=Muhasebe)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    kalem_sayisi: int = 0


class StageUpdate(BaseModel):
    durum: str
    not_: str = Field(default="", alias="not")

    model_config = {"populate_by_name": True}


# ---------- items ----------
class ItemBase(BaseModel):
    urun: str = ""
    adet: int = 1
    genislik_mm: float = 0.0
    acilim_mm: float = 0.0
    yapi_rengi: str = ""
    panel_rengi: str = ""
    aydinlatma: str = ""
    aydinlatma_rengi: str = ""
    led_strip_mtul: float = 0.0
    led_spot_adet: int = 0
    zip_yapi_rengi: str = ""
    zip_kumasi: str = ""
    pergola_kumasi: str = ""
    kumas_profil_rengi: str = ""
    cam_olcusu: str = ""
    cam_rengi: str = ""
    cam_kombinasyonu: str = ""
    tedarikci: str = ""
    birim_fiyat: float = 0.0
    notlar: str = ""


class ProjectItem(ItemBase):
    id: str = Field(default_factory=_uid)
    proje_id: str
    created_at: datetime = Field(default_factory=now_utc)


# ---------- crates ----------
class CrateBase(BaseModel):
    sandik_no: str = ""
    icerik: str = ""
    taban_cm: float = 0.0
    uzunluk_cm: float = 0.0
    yukseklik_cm: float = 0.0
    adet: int = 1
    brut_kg: float = 0.0
    tedarikci: str = ""


class ProjectCrate(CrateBase):
    id: str = Field(default_factory=_uid)
    proje_id: str
    hacim_cbm: float = 0.0
    created_at: datetime = Field(default_factory=now_utc)


def compute_cbm(c: ProjectCrate) -> ProjectCrate:
    c.hacim_cbm = round(c.taban_cm * c.uzunluk_cm * c.yukseklik_cm * max(c.adet, 1) / 1_000_000, 3)
    return c


# ---------- activity ----------
class Activity(BaseModel):
    id: str = Field(default_factory=_uid)
    proje_id: str
    proje_kodu: str = ""
    tip: str  # olusturma | asama | guncelleme | kalem | muhasebe | sandik | not
    mesaj: str
    kullanici: str = ""
    eski_durum: Optional[str] = None
    yeni_durum: Optional[str] = None
    gun: str = ""  # YYYY-MM-DD, server anchored
    created_at: datetime = Field(default_factory=now_utc)


class NoteInput(BaseModel):
    mesaj: str = Field(min_length=1)


# ---------- catalogs (dinamik tanım listeleri) ----------
class CatalogItem(BaseModel):
    id: str = Field(default_factory=_uid)
    tip: str
    deger: str  # kayıtlarda saklanan değer / aşama anahtarı
    label: str  # ekranda görünen ad
    sira: int = 0
    aktif: bool = True
    sistem: bool = False  # çekirdek aşama — silinemez, adı değiştirilebilir
    kullanim: int = 0  # kaç kayıtta kullanıldığı (salt okunur)


class CatalogCreate(BaseModel):
    label: str = Field(min_length=1)
    deger: Optional[str] = None


class CatalogUpdate(BaseModel):
    label: str = Field(min_length=1)
    aktif: bool = True


class CatalogReorder(BaseModel):
    sirali_idler: List[str]


# ---------- proforma revizyonları ----------
class ProformaVersion(BaseModel):
    id: str = Field(default_factory=_uid)
    proje_id: str
    proje_kodu: str = ""
    versiyon: int = 1
    kaynak: str = "manuel"  # manuel | pdf
    aciklama: str = ""
    olusturan: str = ""
    # anlık görüntü
    durum: str = ""
    para_birimi: str = ""
    satis: float = 0.0
    iskonto_tutari: float = 0.0
    transfer_ucreti: float = 0.0
    toplam: float = 0.0
    kalem_sayisi: int = 0
    kalemler: List[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)


class RevisionInput(BaseModel):
    aciklama: str = ""


class ProjectDetail(BaseModel):
    project: Project
    kalemler: List[ProjectItem]
    sandiklar: List[ProjectCrate]
    hareketler: List[Activity]


# ---------- dashboard / reports ----------
class StageCount(BaseModel):
    durum: str
    label: str
    adet: int
    tutar: float


class DeadlineAlert(BaseModel):
    """Termin / yükleme uyarısı — 'gecikti' | 'bugun' | 'yaklasiyor'."""

    proje_id: str
    proje_kodu: str
    proje_adi: str
    musteri: str
    firma: str
    durum: str
    tip: str  # termin | sevk
    tarih: str
    kalan_gun: int
    seviye: str  # gecikti | bugun | yaklasiyor


class DashboardStats(BaseModel):
    toplam_proje: int
    aktif_proje: int
    arsiv_proje: int
    toplam_satis: float
    toplam_tahsilat: float
    kalan_bakiye: float
    net_kar: float
    ortalama_kar_yuzdesi: float
    asamalar: List[StageCount]
    para_birimi_dagilimi: List[StageCount]
    yaklasan_sevkiyatlar: List[Project]
    son_hareketler: List[Activity]
    uyarilar: List[DeadlineAlert]
    geciken_adet: int
    yaklasan_adet: int


# ---------- dealers ----------
class DealerCard(BaseModel):
    anahtar: str  # "firma|ulke"
    firma: str
    ulke: str
    musteriler: List[str]
    proje_adet: int
    aktif_adet: int
    arsiv_adet: int
    para_birimi: str
    ciro: float
    tahsilat: float
    acik_bakiye: float
    net_kar: float
    kar_yuzdesi: float
    son_proje_tarihi: str
    asama_dagilimi: List[StageCount]
    projeler: List[Project]


# ---------- documents ----------
class DocumentMeta(BaseModel):
    id: str = Field(default_factory=_uid)
    proje_id: str
    dosya_adi: str
    kategori: str = "diger"  # cizim | paketleme | beyanname | fatura | proforma | diger
    boyut: int = 0
    content_type: str = ""
    aciklama: str = ""
    yukleyen: str = ""
    file_id: str = ""
    created_at: datetime = Field(default_factory=now_utc)


DOC_CATEGORIES = {
    "cizim": "Teknik Çizim",
    "paketleme": "Paketleme Listesi",
    "beyanname": "Gümrük Beyannamesi",
    "fatura": "Fatura",
    "proforma": "Proforma",
    "diger": "Diğer",
}


class DailyReport(BaseModel):
    tarih: str
    yeni_projeler: List[Project]
    asama_degisimleri: List[Activity]
    sevk_edilenler: List[Project]
    tum_hareketler: List[Activity]
    gun_satis: float
    gun_tahsilat: float
    aktif_proje: int
