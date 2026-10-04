// Hand-written mirrors of the Pydantic models in backend/models/schemas.py.
// Change one side, change the other in the same edit.

export interface User {
  id: string;
  email: string;
  ad_soyad: string;
  rol: string;
  created_at: string;
}

export interface Odeme {
  tutar: number;
  tarih: string | null;
  not: string;
}

export interface Muhasebe {
  satis: number;
  alis: number;
  iskonto_tutari: number;
  transfer_ucreti: number;
  fatura_tipi: string;
  odeme_durumu: string;
  odemeler: Odeme[];
  transfer_dahil_toplam_satis: number;
  net_kar: number;
  kar_yuzdesi: number;
  toplam_tahsilat: number;
  kalan_bakiye: number;
}

export interface Project {
  id: string;
  proje_kodu: string;
  firma: string;
  musteri: string;
  ulke: string;
  proje_tarihi: string;
  proje_adi: string;
  tedarikci: string;
  durum: string;
  arsiv: boolean;
  musteri_onay_tarihi: string | null;
  tedarikci_onay_tarihi: string | null;
  sevk_tarihi: string | null;
  termin_tarihi: string | null;
  montaj_tipi: string;
  para_birimi: string;
  satis_tipi: string;
  lojistik_firmasi: string;
  rezervasyon_kodu: string;
  konteyner_no: string;
  gumruk_musavirligi: string;
  beyanname_no: string;
  notlar: string;
  muhasebe: Muhasebe;
  created_at: string;
  updated_at: string;
  kalem_sayisi: number;
}

export interface ProjectItem {
  id: string;
  proje_id: string;
  urun: string;
  adet: number;
  genislik_mm: number;
  acilim_mm: number;
  yapi_rengi: string;
  panel_rengi: string;
  aydinlatma: string;
  aydinlatma_rengi: string;
  led_strip_mtul: number;
  led_spot_adet: number;
  zip_yapi_rengi: string;
  zip_kumasi: string;
  pergola_kumasi: string;
  kumas_profil_rengi: string;
  cam_olcusu: string;
  cam_rengi: string;
  cam_kombinasyonu: string;
  tedarikci: string;
  birim_fiyat: number;
  notlar: string;
  created_at: string;
}

export interface ProjectCrate {
  id: string;
  proje_id: string;
  sandik_no: string;
  icerik: string;
  taban_cm: number;
  uzunluk_cm: number;
  yukseklik_cm: number;
  adet: number;
  brut_kg: number;
  tedarikci: string;
  hacim_cbm: number;
  created_at: string;
}

export interface Activity {
  id: string;
  proje_id: string;
  proje_kodu: string;
  tip: string;
  mesaj: string;
  kullanici: string;
  eski_durum: string | null;
  yeni_durum: string | null;
  gun: string;
  created_at: string;
}

export interface ProjectDetail {
  project: Project;
  kalemler: ProjectItem[];
  sandiklar: ProjectCrate[];
  hareketler: Activity[];
}

export interface StageCount {
  durum: string;
  label: string;
  adet: number;
  tutar: number;
}

export interface CatalogItem {
  id: string;
  tip: string;
  deger: string;
  label: string;
  sira: number;
  aktif: boolean;
  sistem: boolean;
  kullanim: number;
}

export interface ProformaVersion {
  id: string;
  proje_id: string;
  proje_kodu: string;
  versiyon: number;
  kaynak: string;
  aciklama: string;
  olusturan: string;
  durum: string;
  para_birimi: string;
  satis: number;
  iskonto_tutari: number;
  transfer_ucreti: number;
  toplam: number;
  kalem_sayisi: number;
  kalemler: Record<string, unknown>[];
  created_at: string;
}

export interface DeadlineAlert {
  proje_id: string;
  proje_kodu: string;
  proje_adi: string;
  musteri: string;
  firma: string;
  durum: string;
  tip: string;
  tarih: string;
  kalan_gun: number;
  seviye: string;
}

export interface DealerCard {
  anahtar: string;
  firma: string;
  ulke: string;
  musteriler: string[];
  proje_adet: number;
  aktif_adet: number;
  arsiv_adet: number;
  para_birimi: string;
  ciro: number;
  tahsilat: number;
  acik_bakiye: number;
  net_kar: number;
  kar_yuzdesi: number;
  son_proje_tarihi: string;
  asama_dagilimi: StageCount[];
  projeler: Project[];
}

export interface DocumentMeta {
  id: string;
  proje_id: string;
  dosya_adi: string;
  kategori: string;
  boyut: number;
  content_type: string;
  aciklama: string;
  yukleyen: string;
  file_id: string;
  created_at: string;
}

export interface DashboardStats {
  toplam_proje: number;
  aktif_proje: number;
  arsiv_proje: number;
  toplam_satis: number;
  toplam_tahsilat: number;
  kalan_bakiye: number;
  net_kar: number;
  ortalama_kar_yuzdesi: number;
  asamalar: StageCount[];
  para_birimi_dagilimi: StageCount[];
  yaklasan_sevkiyatlar: Project[];
  son_hareketler: Activity[];
  uyarilar: DeadlineAlert[];
  geciken_adet: number;
  yaklasan_adet: number;
}

export interface CurrencyTotal {
  para_birimi: string;
  proje_adet: number;
  satis: number;
  tahsilat: number;
  bakiye: number;
  net_kar: number;
}

export interface DailyReport {
  tarih: string;
  yeni_projeler: Project[];
  asama_degisimleri: Activity[];
  sevk_edilenler: Project[];
  tum_hareketler: Activity[];
  gun_satis: number;
  gun_tahsilat: number;
  aktif_proje: number;
  gun_satis_dagilimi: CurrencyTotal[];
  gun_tahsilat_dagilimi: CurrencyTotal[];
  genel_dagilim: CurrencyTotal[];
}

// Payloads
export type ProjectPayload = Omit<
  Project,
  "id" | "proje_kodu" | "muhasebe" | "created_at" | "updated_at" | "kalem_sayisi"
> & { proje_kodu?: string };

export type ItemPayload = Omit<ProjectItem, "id" | "proje_id" | "created_at">;
export type CratePayload = Omit<ProjectCrate, "id" | "proje_id" | "created_at" | "hacim_cbm">;

// ---------- bayi portalı ----------
export interface DealerAccount {
  id: string;
  email: string;
  firma: string;
  ulke: string;
  yetkili: string;
  aktif: boolean;
  created_at: string;
}

export interface PortalProject {
  proje_kodu: string;
  proje_adi: string;
  musteri: string;
  durum: string;
  durum_label: string;
  proje_tarihi: string;
  termin_tarihi: string | null;
  sevk_tarihi: string | null;
  para_birimi: string;
  toplam_satis: number;
  tahsilat: number;
  bakiye: number;
  odeme_durumu: string;
  arsiv: boolean;
}

export interface PortalSummary {
  firma: string;
  ulke: string;
  yetkili: string;
  para_birimi: string;
  proje_adet: number;
  aktif_adet: number;
  toplam_satis: number;
  toplam_tahsilat: number;
  acik_bakiye: number;
  projeler: PortalProject[];
}

// ---------- yetkilendirme ----------
export interface Role {
  kod: string;
  label: string;
  yetkiler: string[];
  sistem: boolean;
}

export interface UserAccount {
  id: string;
  email: string;
  ad_soyad: string;
  rol: string;
  created_at: string;
}

export interface MyPermissions {
  rol: string;
  rol_label: string;
  yetkiler: string[];
}

// ---------- döviz kuru ----------
export interface ExchangeRate {
  para_birimi: string;
  kur: number;
  guncellenme: string;
  guncelleyen: string;
}

// ---------- aylık rapor ----------
export interface DealerMonthRow {
  firma: string;
  ulke: string;
  proje_adet: number;
  satis_try: number;
  tahsilat_try: number;
}

export interface MonthlyReport {
  ay: string;
  proje_adet: number;
  kur_dagilimi: CurrencyTotal[];
  try_satis: number;
  try_tahsilat: number;
  try_bakiye: number;
  try_net_kar: number;
  kurlar: ExchangeRate[];
  eksik_kurlar: string[];
  asama_dagilimi: StageCount[];
  bayi_ozeti: DealerMonthRow[];
}

// ---------- portal evrakları ----------
export interface PortalDocument {
  id: string;
  proje_kodu: string;
  dosya_adi: string;
  kategori: string;
  boyut: number;
  aciklama: string;
  created_at: string;
}

// ---------- marka ayarları ----------
export interface Branding {
  program_adi: string;
  alt_baslik: string;
  logo_var: boolean;
}

// ---------- toplu işlem ----------
export interface BulkResult {
  etkilenen: number;
  bulunamayan: number;
}

export interface TrashItem {
  id: string;
  proje_kodu: string;
  proje_adi: string;
  firma: string;
  musteri: string;
  silindi_at: string;
  silen: string;
  kalan_gun: number;
  kalem_adet: number;
  sandik_adet: number;
}
