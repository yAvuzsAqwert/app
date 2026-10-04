# Pergola & Tente Proje Takip — Spec

## Ne yapar
Pergola, tente, sürme/giyotin cam ve bioklimatik sistem ihracat/yurtiçi projelerinin
uçtan uca takibi: talep → proforma → revizyon → onay → üretim → paketleme (sandık) →
lojistik rezervasyon → sevk → fatura → gümrük beyannamesi → tamamlandı (11 aşama).

## Stack
FastAPI + MongoDB (motor) / Vite + React 19 + TS strict + Tailwind v4 + shadcn (base-nova).
Tüm endpointler `api_router` üzerinde `/api` altında. Frontend `src/lib/api.ts` ile relatif çağırır.

## Veri modeli (backend/models/schemas.py)
- `users` — email, ad_soyad, sifre_hash (pbkdf2)
- `sessions` — token (httpOnly cookie `pergola_session`), 30 gün TTL
- `projects` — proje_kodu (PRG-YYYY-NNN, unique), firma, musteri, ulke, proje_adi, tedarikci,
  durum (11 aşama key), arsiv, proje/müşteri onay/tedarikçi onay/sevk/termin tarihleri,
  montaj_tipi, para_birimi, satis_tipi, lojistik_firmasi, rezervasyon_kodu, konteyner_no,
  gumruk_musavirligi, beyanname_no, notlar, embedded `muhasebe`
- `muhasebe` (embedded) — satis, alis, iskonto_tutari, transfer_ucreti, fatura_tipi,
  odemeler[5] (tutar/tarih/not) + türetilmiş: transfer_dahil_toplam_satis, net_kar,
  kar_yuzdesi, toplam_tahsilat, kalan_bakiye, odeme_durumu. Hesaplama SADECE backend
  `compute_muhasebe()` içinde (frontend sadece anlık önizleme gösterir).
- `project_items` — ürün, adet, genislik_mm, acilim_mm, yapı/panel rengi, aydınlatma,
  led_strip_mtul, led_spot_adet, zip/pergola kumaş, cam ölçü/renk/kombinasyon, tedarikçi, birim_fiyat
- `project_crates` — sandik_no, icerik, taban/uzunluk/yukseklik_cm, adet, brut_kg, hacim_cbm (auto)
- `activities` — her aşama/kalem/sandık/muhasebe/not işlemi loglanır, `gun` alanı server-anchored

## Ek modüller (2. tur)
- **Bayi kartları** (`routers/dealers.py`): projeler `firma|ulke` anahtarıyla gruplanır; ciro,
  tahsilat, açık bakiye, net kar, kar %, aşama dağılımı ve proje listesi döner. Bayi birden fazla
  para birimi taşıyorsa `para_birimi` = "KARMA".
- **Termin uyarıları** (`routers/projects.py::build_alerts`): 7 günlük pencere, `today_iso()`
  anchorlı. `termin_tarihi` ve `sevk_tarihi` için ayrı uyarı; seviye `gecikti|bugun|yaklasiyor`.
  Sevk sonrası aşamalar (yuklendi_sevk, fatura, gumruk_beyanname, tamamlandi) ve arşiv hariç.
- **Proforma PDF** (`routers/proforma.py`): reportlab + Liberation Sans (Türkçe glif). Başlık
  `COMPANY_NAME` env (varsayılan **DIAGONAL**). Kalem tablosu teknik özellik satırıyla, iskonto /
  transfer / genel toplam, banka + not bloğu.
- **Evraklar** (`routers/documents.py`): GridFS bucket `evraklar` + `documents` meta koleksiyonu.
  Maks 10 MB; pdf/resim/xlsx/docx/dwg/dxf/csv/txt. Kategoriler: cizim, paketleme, beyanname,
  fatura, proforma, diger. Disk kullanılmaz (deploy güvenli).

## Endpointler
`/api/auth/{register,login,logout,me}`, `/api/projects` (CRUD + `?durum&arsiv&satis_tipi&q`),
`/api/projects/{id}` (detail: project+kalemler+sandiklar+hareketler),
`PATCH /api/projects/{id}/stage`, `PATCH /api/projects/{id}/archive`,
`PUT /api/projects/{id}/muhasebe`, `/api/projects/{id}/kalemler`, `/api/kalemler/{id}`,
`/api/projects/{id}/sandiklar`, `/api/sandiklar/{id}`, `/api/projects/{id}/notlar`,
`/api/dashboard`, `/api/stages`, `/api/alerts`, `/api/reports/daily`,
`/api/reports/daily/export` (xlsx), `/api/dealers`, `/api/dealers/{anahtar}`,
`/api/projects/{id}/proforma` (pdf), `/api/projects/{id}/evraklar` (GET+POST multipart),
`/api/evraklar/{id}/indir`, `DELETE /api/evraklar/{id}`, `/api/evrak-kategorileri`.

## Rotalar (frontend)
`/giris` (public), `/panel`, `/projeler`, `/projeler/:id`, `/bayiler`, `/rapor` — hepsi cookie session ile korumalı.
Proje detay sekmeleri: Ürün Kalemleri, Muhasebe & Tahsilat, Sandık & Sevkiyat, Proje Bilgileri, Evraklar, İşlem Geçmişi.

## Seed (backend/seed.py — idempotent, koleksiyonları sıfırlar)
11 proje (PRG-2026-001..011) Almanya/Fransa/BAE/Hollanda/Türkiye/Irak/İngiltere/Avusturya,
farklı aşamalarda, kalemler + sandıklar + 5 taksit ödeme + aktivite kayıtları. 2 kullanıcı.

## Login
memory/test_credentials.md içinde.
