// Shared vocabulary: the 11 pipeline stages mirror STAGES/STAGE_LABELS in backend/models/schemas.py.

export interface Stage {
  key: string;
  label: string;
  short: string;
  tone: string;
}

export const STAGES: Stage[] = [
  { key: "talep_alindi", label: "Talep Alındı", short: "Talep", tone: "text-sky-300 bg-sky-500/10 border-sky-500/30" },
  { key: "teklif_proforma", label: "Teklif / Proforma", short: "Teklif", tone: "text-blue-300 bg-blue-500/10 border-blue-500/30" },
  { key: "revizyon", label: "Revizyon", short: "Revizyon", tone: "text-amber-300 bg-amber-500/10 border-amber-500/30" },
  { key: "musteri_onayi", label: "Müşteri Onayı", short: "Onay", tone: "text-emerald-300 bg-emerald-500/10 border-emerald-500/30" },
  { key: "uretim", label: "Üretim", short: "Üretim", tone: "text-indigo-300 bg-indigo-500/10 border-indigo-500/30" },
  { key: "paketleme", label: "Paketleme / Sandık", short: "Paketleme", tone: "text-yellow-300 bg-yellow-500/10 border-yellow-500/30" },
  { key: "lojistik_rezervasyon", label: "Lojistik / Rezervasyon", short: "Lojistik", tone: "text-orange-300 bg-orange-500/10 border-orange-500/30" },
  { key: "yuklendi_sevk", label: "Yüklendi / Sevk", short: "Sevk", tone: "text-cyan-300 bg-cyan-500/10 border-cyan-500/30" },
  { key: "fatura", label: "Fatura", short: "Fatura", tone: "text-teal-300 bg-teal-500/10 border-teal-500/30" },
  { key: "gumruk_beyanname", label: "Gümrük / Beyanname", short: "Gümrük", tone: "text-purple-300 bg-purple-500/10 border-purple-500/30" },
  { key: "tamamlandi", label: "Tamamlandı", short: "Tamam", tone: "text-emerald-200 bg-emerald-500/20 border-emerald-400/40" },
];

export const stageOf = (key: string): Stage =>
  STAGES.find((s) => s.key === key) ?? {
    key,
    label: key,
    short: key,
    tone: "text-slate-300 bg-slate-500/10 border-slate-500/30",
  };

export const stageIndex = (key: string) => STAGES.findIndex((s) => s.key === key);

export const PARA_BIRIMLERI = ["EUR", "USD", "TRY", "GBP"];
export const SATIS_TIPLERI: Record<string, string> = { ihracat: "İhracat", yurtici: "Yurt İçi" };
export const FATURA_TIPLERI: Record<string, string> = {
  ihrac_kayitli: "İhraç Kayıtlı",
  kdvli: "KDV'li",
  kdv_muaf: "KDV Muaf",
};
export const ODEME_DURUMLARI: Record<string, string> = {
  bekliyor: "Bekliyor",
  kismi: "Kısmi Tahsilat",
  tamamlandi: "Tamamlandı",
};

export const URUN_TIPLERI = [
  "Bioklimatik Pergola (Alüminyum Lamelli)",
  "Montaja Hazır Pergola (PVC Kumaşlı)",
  "Sürme Cam Sistemi (3 Raylı)",
  "Sürme Cam Sistemi (5 Raylı)",
  "Giyotin Cam Sistemi (Motorlu)",
  "Giyotin Cam Sistemi (Zincirli)",
  "Zip Perde / Dış Cephe Güneş Kırıcı",
  "Kasetli Tente / Mafsallı Tente",
  "Sabit Cam Tavan & Kış Bahçesi",
];

export const MONTAJ_TIPLERI = ["Duvara Montaj", "Serbest Ayaklı", "Ankastre", "Köşe Montaj"];

export const DOC_CATEGORIES: Record<string, string> = {
  cizim: "Teknik Çizim",
  paketleme: "Paketleme Listesi",
  beyanname: "Gümrük Beyannamesi",
  fatura: "Fatura",
  proforma: "Proforma",
  diger: "Diğer",
};

export const ALERT_TONES: Record<string, string> = {
  gecikti: "text-red-300 bg-red-500/15 border-red-500/40",
  bugun: "text-orange-200 bg-orange-500/20 border-orange-400/50",
  yaklasiyor: "text-amber-300 bg-amber-500/10 border-amber-500/30",
};

export const ALERT_LABELS: Record<string, string> = {
  gecikti: "Gecikti",
  bugun: "Bugün",
  yaklasiyor: "Yaklaşıyor",
};

export const alertText = (kalan: number) => {
  if (kalan < 0) return `${Math.abs(kalan)} gün gecikti`;
  if (kalan === 0) return "Bugün";
  return `${kalan} gün kaldı`;
};

export const fmtBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
};

export const fmtMoney = (value: number, currency = "") =>
  `${new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(
    value || 0,
  )}${currency ? ` ${currency}` : ""}`;

export const fmtDate = (value?: string | null) => {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric" });
};

export const fmtDateTime = (value?: string | null) => {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};
