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

## Sürüm 3 — Tanımlar, Revizyon, Ekstre, Etiket (güncel)
- **Tanım katalogları** (`lib/catalog.py`, `routers/catalogs.py`, `/tanimlar` → `pages/Settings.tsx`):
  15 liste tipi (surec_asamasi, urun, yapi_rengi, panel_rengi, cam_kombinasyonu, cam_rengi,
  kumas, aydinlatma, montaj_tipi, firma, musteri, tedarikci, lojistik_firmasi, para_birimi,
  fatura_tipi). Tam CRUD + sıra değiştirme (`PATCH /api/catalogs/{tip}/reorder`) + aktif/pasif.
  Kullanımda olan kayıt silinemez (409 + uyarı). Değerler `Projeler.xlsx` gerçek verisinden
  seed edilir (90 ürün, 26 yapı rengi, 16 tedarikçi, 34 firma, 20 müşteri vb.).
  Proje formları ve aşama doğrulaması artık bu listelerden dinamik beslenir.
- **Proforma revizyon geçmişi** (`routers/revisions.py`): her versiyon kalem + tutar anlık görüntüsü.
  Proforma PDF indirildiğinde otomatik (`kaynak=pdf`), "Revizyon Kaydet" ile notlu manuel kayıt.
  Proje detayında versiyon listesi ve iki versiyonun yan yana karşılaştırması.
  `GET/POST /api/projects/{id}/revizyonlar`, `DELETE /api/revizyonlar/{id}`.
- **Bayi ekstresi** (`GET /api/reports/dealer-statement?anahtar=firma|ulke`): tek Excel dosyası,
  5 sayfa — Bayi Ozeti, Projeler, Tahsilat Dokumu, Proje Kalemleri, Sandik Listesi.
  Bayi Kartları sayfasındaki "Ekstre (Excel)" butonundan indirilir. Dosya adı ASCII-safe.
- **Sandık etiketleri** (`routers/labels.py`, `GET /api/projects/{id}/sandik-etiketleri`):
  A4'e 2×2 = 4 etiket; sandık no, proje, müşteri, ülke, içerik, ölçü/hacim/brüt kg,
  tedarikçi, aşama, lojistik/rezervasyon/konteyner bilgisi.
- **Gecikme bildirimi**: e-posta kurulmadı (kullanıcı kararı) — yalnızca uygulama içi
  7 günlük uyarı paneli (`/api/alerts`, panel + proje listesi göstergeleri).
- **Teknik çizim sayfası**: Evraklar sekmesinde "Çizim" kategorisiyle yüklenen resimler
  (png/jpg/jpeg/webp/gif, en çok 20 adet) proforma PDF'inin sonuna `PageBreak` ile eklenen
  "TEKNİK ÇİZİMLER" sayfasında 2'li ızgarada, açıklama alt yazısıyla basılır
  (`routers/proforma.py::_drawing_flowables`). Resim olmayan çizim evrakları atlanır.

## Sürüm 4 — Hızlı tanım ekleme, Bayi Portalı, Para birimi kırılımı
- **CatalogSelect** (`frontend/src/components/CatalogSelect.tsx`): tanım listesinden seçim +
  "Yeni ekle" satır içi girişi. Kalem (sipariş) formundaki ürün/yapı rengi/panel rengi/
  aydınlatma/zip yapı rengi/zip-pergola kumaşı/cam rengi/cam kombinasyonu/tedarikçi,
  sandık formundaki tedarikçi ve yeni proje formundaki firma/müşteri/tedarikçi/para birimi/
  montaj tipi alanları artık bu bileşeni kullanır — ekrandan ayrılmadan tanım oluşturulur
  (`POST /api/catalogs/{tip}`), oluşan değer otomatik seçilir.
- **Bayi Portalı** (`routers/portal.py`, `pages/PortalLogin.tsx`, `pages/Portal.tsx`):
  salt okunur, ayrı cookie (`bayi_session`) ve ayrı koleksiyonlar (`dealer_accounts`,
  `dealer_sessions`). Rotalar: `/bayi-giris`, `/bayi`.
  Endpointler: `POST /api/portal/login|logout`, `GET /api/portal/me`, `GET /api/portal/ozet`
  (bayinin firma+ülke eşleşen projeleri, tutar/tahsilat/bakiye), ekip tarafında
  `GET/POST /api/dealer-accounts`, `DELETE /api/dealer-accounts/{id}` (Bayi Kartları sayfasında
  "Portal Hesabı Ver"). Portal cookie'si ekip endpointlerine erişemez (401).
- **Para birimi kırılımı**: `GET /api/reports/daily` artık `gun_satis_dagilimi`,
  `gun_tahsilat_dagilimi`, `genel_dagilim` (CurrencyTotal: para_birimi, proje_adet, satis,
  tahsilat, bakiye, net_kar) döner; farklı kurlar asla tek toplamda birleştirilmez.
  Günlük Rapor sayfasında para birimli kartlar + "Para Birimine Göre Kırılım" tablosu;
  Excel raporunda yeni "Para Birimi Dagilimi" sayfası, Projeler sayfasında tutar kolonları
  para birimi etiketli (örn. "43400.00 EUR"), Proje Kalemleri sayfasında para birimi +
  birim fiyat/satır tutarı para birimli.

## Sürüm 5 — Yetkilendirme, kur çevirisi, aylık rapor, portal evrakları
- **Rol tabanlı yetkilendirme** (`backend/lib/permissions.py`, `routers/admin.py`,
  `frontend/src/pages/Users.tsx`, `/kullanicilar`): 20 yetki kodu, 5 hazır rol
  (admin / satis / uretim / muhasebe / izleyici). Roller `roles` koleksiyonunda,
  yetkiler ekrandan işaretlenerek düzenlenir; **admin rolü daima tüm yetkilere sahiptir
  ve kilitlidir (PUT /roles/admin → 409)**. Kullanıcı `rol` alanı taşır; rol her istekte
  veritabanından okunur (istemciden asla). Yetkisiz işlem → 403, varsayılan reddet.
  Korumalar: en az bir admin kalmalı, kendi hesabını silemez.
  Endpointler: `GET /api/permissions`, `GET/PUT /api/roles[/{kod}]`,
  `GET/POST /api/users`, `PUT /api/users/{id}/rol`, `DELETE /api/users/{id}`,
  `GET /api/my-permissions`. Arayüz (menü + butonlar) `usePermissions().can()` ile sadeleşir,
  gerçek kontrol sunucudadır.
- **Döviz kuru** (`GET /api/kurlar`, `PUT /api/kurlar` → `kur:yonet`): elle girilen TRY bazlı
  kurlar (`rates` koleksiyonu, 1 birim = kaç TRY). Tanımlar sayfasının altındaki
  "Döviz Kurları" kartından güncellenir.
- **Aylık rapor** (`GET /api/reports/monthly?ay=YYYY-MM`, `/monthly/export`, sayfa `/aylik-rapor`):
  kur bazında ciro/tahsilat/bakiye/kar + kurlarla hesaplanan TRY karşılığı özet toplam,
  aşama özeti, bayi özeti; Excel 5 sayfa (Ay Ozeti, Kur Bazinda, Asama Ozeti, Bayi Ozeti,
  Projeler). Kuru girilmemiş para birimleri `eksik_kurlar` ile uyarı olarak gösterilir.
- **Portal evrakları**: bayi kendi projelerinin proformasını (`GET /api/portal/projeler/{kod}/proforma`,
  revizyon kaydı oluşturmaz) ve yalnızca "Çizim" kategorisindeki evraklarını
  (`GET /api/portal/evraklar`, `/portal/evraklar/{id}/indir`) indirebilir.
  Başka bayinin kaydı 404 döner (varlık sızdırmaz).
- Kendi kendine kayıt (`POST /api/auth/register`) artık **izleyici** rolüyle açılır;
  yetkiyi admin `/kullanicilar` ekranından yükseltir.

## Sürüm 6 — Marka ayarları
- **Program adı & logo** (`backend/routers/branding.py`, Tanımlar → "Program Adı & Logo" kartı):
  `settings` koleksiyonunda `key="branding"` dokümanı (program_adi, alt_baslik),
  logo GridFS bucket `branding` içinde (PNG/JPG/WEBP/SVG, maks 2 MB).
  Endpointler: `GET /api/branding` ve `GET /api/branding/logo` oturum istemez (giriş
  ekranı ve bayi portalı da kullanır); `PUT /api/branding`, `POST/DELETE /api/branding/logo`
  → `tanim:yonet` yetkisi. Arayüzde `useBranding()` ile yan menü, giriş ekranı ve portal
  başlığı beslenir.
- Menü ve sayfa başlığı "Komuta Paneli" → **"Kontrol Paneli"** olarak değiştirildi.

## Güvenlik denetimi düzeltmeleri (sürüm 6.1)
- Açık kayıt kapatıldı: `POST /api/auth/register` artık `kullanici:yonet` ister, oturum açmaz;
  giriş ekranından kayıt/demo şifre paneli kaldırıldı.
- Yeni yetki `evrak:goruntule`: evrak listeleme ve indirme bu yetkiyi ister (izleyici'de yok).
- Finansal maskeleme: `muhasebe:goruntule` yetkisi olmayan kullanıcıya proje listesi/detayı ve
  panel toplamlarında muhasebe alanları sıfır döner; `/api/dealers*` artık
  `bayi:goruntule` + `muhasebe:goruntule` ister.
- NoSQL regex sertleştirme: aylık rapor dönemi `^\d{4}-(0[1-9]|1[0-2])$` ile doğrulanır,
  proje aramasında `re.escape` + 80 karakter sınırı.
- Oturum çerezleri `Secure`, `CORS_ORIGINS` tek kaynağa sabitlendi, `dealer_sessions` 14 gün TTL,
  evrak indirme `Content-Disposition` dosya adı ASCII-safe temizlenir.
- `seed.py` şifreleri koddan kaldırıldı (`SEED_PASSWORD` env ya da rastgele); canlı demo
  hesaplarının şifreleri döndürüldü ve tüm eski oturumlar iptal edildi.

## Üretim hata düzeltmesi (sürüm 6.2) — "attached to a different loop"
- `backend/lib/db.py`: Motor istemcisi artık import sırasında değil, ilk kullanımda
  (`get_client()` / `get_db()`) oluşturulur; `db` ve `client` tembel proxy'lerdir.
  Sebep: üretim entrypoint'i `--reload` içermediği için import-zamanı event loop,
  servis eden loop'tan farklı oluyor ve DB'ye dokunan her uç 500 veriyordu.
- GridFS bucket'ları modül düzeyinden fonksiyon içine taşındı
  (`routers/branding.py`, `routers/documents.py`, `routers/proforma.py` → `_bucket()`;
  `routers/portal.py` → `get_db()`), böylece onlar da servis eden loop'a bağlanır.
- `MONGO_URL` yanında `MONGODB_URI`/`MONGO_URI`/`DATABASE_URL` da okunur; `DB_NAME` yoksa `app`.
- Yeni teşhis ucu `GET /api/health` → `{ok, db, kullanici, proje}` (gizli bilgi içermez).
- CORS: kimlik bilgili isteklerde `*` kullanılmaz; `CORS_ORIGINS` listesinden wildcard atılır,
  `CORS_ORIGIN_REGEX` ile `*.emergentagent.com`, `*.emergent.host`, `*.diagonalventure.com`
  origin'leri kabul edilir ve yanıtta tam origin + `allow-credentials: true` döner.

## Sürüm 6.3 — Şifre yönetimi
- `PUT /api/auth/sifre` (oturum sahibi): mevcut şifre doğrulanır, yeni şifre en az 8 karakter,
  değişiklik sonrası kullanıcının tüm oturumları kapatılır. Arayüz: yan menüdeki
  "Şifremi Değiştir" (components/PasswordDialog.tsx).
- `PUT /api/users/{id}/sifre` (`kullanici:yonet`): yönetici başka kullanıcının şifresini sıfırlar,
  o kullanıcının oturumları kapatılır. Arayüz: Kullanıcılar & Yetkiler tablosunda anahtar ikonu.

## Sürüm 6.4 — PDF Türkçe karakter + yazdırma
- PDF fontu (`LiberationSans-Regular/Bold.ttf`) artık depoya gömülü:
  `backend/assets/fonts/`. `routers/proforma.py::_register_fonts` önce gömülü dizine,
  sonra sistem dizinine bakar; font yoksa Helvetica'ya DÜŞMEZ, 500 ile uyarır
  (eski davranışta üretim imajında sistem fontu olmadığı için Türkçe karakterler bozuluyordu).
  Proforma, sandık etiketi ve proje dosyası PDF'lerinin tümü aynı fontu kullanır.
- **Proje dosyası PDF'i** (`routers/printouts.py`, `GET /api/projects/{id}/dosya.pdf`,
  yetki `proje:goruntule`, `Content-Disposition: inline` → tarayıcıdan doğrudan yazdırılır):
  proje künyesi, ürün kalemleri, muhasebe (yalnızca `muhasebe:goruntule` varsa),
  sandık/paketleme listesi, revizyon geçmişi ve evrak listesi. Proje detay sayfasındaki
  "Proje ve Detaylarını Yazdır" butonu.
- **Evrak yazdırma**: `GET /api/evraklar/{id}/goruntule` (inline, `evrak:goruntule`) —
  evrak satırındaki yazıcı ikonu dosyayı yeni sekmede açar, tarayıcıdan yazdırılabilir.

## Sürüm 6.5 — Giriş (e-posta + şifre) gözden geçirme ve sertleştirme
Mevcut akış doğrulandı: `POST /api/auth/login` (e-posta küçük harfe normalize edilir,
pbkdf2-sha256 120k tur + kullanıcı başına salt), oturum httpOnly + Secure + SameSite=Lax
çerezde (`pergola_session`), `sessions` koleksiyonunda 30 gün TTL, `GET /api/auth/me`,
`POST /api/auth/logout` (sunucu tarafında oturumu siler), `PUT /api/auth/sifre`.
Eklenenler:
- **Brute-force koruması**: `login_attempts` koleksiyonu (1 saat TTL) — aynı e-posta+IP için
  15 dakikada 10 hatalı denemeden veya aynı e-posta için 20 denemeden sonra `429`.
  Başarılı girişte o e-postanın denemeleri temizlenir. IP, `X-Forwarded-For` ilk girdisinden
  alınır (ters vekil arkasında doğru çalışır).
- Giriş ekranı hata mesajları netleşti (401 / 429 / sunucu hatası / ağ hatası ayrı ayrı).

## Sürüm 6.6 — Proje silme (arayüz)
- `DELETE /api/projects/{id}` (yetki `proje:sil`) projeyi, ürün kalemlerini, sandıklarını ve
  işlem geçmişini birlikte siler; olmayan kayıt 404.
- Arayüz: Projeler listesindeki her satırda çöp kutusu ikonu ve proje detay sayfasının
  üstünde "Projeyi Sil" butonu. Her ikisi de onay diyaloğu açar
  (`delete-project-dialog`, "Vazgeç" / "Kalıcı Olarak Sil") ve arşivleme alternatifini hatırlatır.
  Yetkisi olmayan kullanıcıda butonlar devre dışıdır; detaydan silince `/projeler`e dönülür.

## Sürüm 6.7 — İşlem günlüğü + toplu işlem
- **İşlem günlüğü** (`routers/audit.py`, sayfa `/islem-gunlugu`): `activities` koleksiyonundan
  tarih/saat, kullanıcı, işlem tipi, proje ve açıklama ile liste.
  `GET /api/activities?kullanici=&tip=&baslangic=&bitis=&limit=` ve
  `GET /api/activities/kullanicilar`; yeni yetki **`islem_log:goruntule`** (varsayılan: yalnız admin).
  Silme kayıtları kırmızı etiketle görünür; aşama değişimleri eski → yeni durumu gösterir.
- **Toplu işlem** (Projeler listesinde satır seçim kutuları + "x proje seçildi" çubuğu):
  `POST /api/projects/bulk/archive` (`{ids, arsiv}`) ve `POST /api/projects/bulk/delete`
  (`{ids}`) — yetki `proje:sil`, boş liste 400, yanıt `{etkilenen, bulunamayan}`.
  Toplu silme onay diyaloğu ister ve her proje için günlüğe "Toplu silme" kaydı yazar.
