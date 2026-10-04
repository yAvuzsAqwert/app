// Hand-written mirrors of the Pydantic models in backend/models/schemas.py.
// Change one side, change the other in the same edit.

export interface User {
  id: string;
  email: string;
  ad_soyad: string;
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
}

// Payloads
export type ProjectPayload = Omit<
  Project,
  "id" | "proje_kodu" | "muhasebe" | "created_at" | "updated_at" | "kalem_sayisi"
> & { proje_kodu?: string };

export type ItemPayload = Omit<ProjectItem, "id" | "proje_id" | "created_at">;
export type CratePayload = Omit<ProjectCrate, "id" | "proje_id" | "created_at" | "hacim_cbm">;
