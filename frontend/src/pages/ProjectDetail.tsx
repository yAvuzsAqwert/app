import { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowLeft,
  Check,
  CreditCard,
  History,
  Layers,
  Package,
  Pencil,
  Plus,
  Save,
  Trash2,
  FileText,
  StickyNote,
  FileDown,
  Paperclip,
  Upload,
  Download,
  Printer,
  Tags,
  GitCompare,
} from "lucide-react";
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, ApiError } from "@/lib/api";
import type {
  CratePayload,
  DocumentMeta,
  ItemPayload,
  Muhasebe,
  ProformaVersion,
  ProjectDetail as ProjectDetailT,
  ProjectPayload,
} from "@/lib/types";
import {
  DOC_CATEGORIES,
  fmtBytes,
  FATURA_TIPLERI,
  MONTAJ_TIPLERI,
  ODEME_DURUMLARI,
  PARA_BIRIMLERI,
  SATIS_TIPLERI,
  STAGES,
  URUN_TIPLERI,
  fmtDate,
  fmtDateTime,
  fmtMoney,
  stageIndex,
} from "@/lib/constants";
import { PageHeader, EmptyState } from "@/components/AppShell";
import { StageBadge } from "@/components/StageBadge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useOptions } from "@/lib/useCatalogs";
import CatalogSelect from "@/components/CatalogSelect";
import { usePermissions } from "@/lib/usePermissions";

function errText(err: unknown) {
  if (err instanceof ApiError) {
    const body = err.body as { detail?: unknown } | null;
    if (body && typeof body.detail === "string") return body.detail;
  }
  return "İşlem başarısız oldu";
}

const emptyItem = (): ItemPayload => ({
  urun: URUN_TIPLERI[0],
  adet: 1,
  genislik_mm: 0,
  acilim_mm: 0,
  yapi_rengi: "",
  panel_rengi: "",
  aydinlatma: "",
  aydinlatma_rengi: "",
  led_strip_mtul: 0,
  led_spot_adet: 0,
  zip_yapi_rengi: "",
  zip_kumasi: "",
  pergola_kumasi: "",
  kumas_profil_rengi: "",
  cam_olcusu: "",
  cam_rengi: "",
  cam_kombinasyonu: "",
  tedarikci: "",
  birim_fiyat: 0,
  notlar: "",
});

const emptyCrate = (): CratePayload => ({
  sandik_no: "",
  icerik: "",
  taban_cm: 0,
  uzunluk_cm: 0,
  yukseklik_cm: 0,
  adet: 1,
  brut_kg: 0,
  tedarikci: "",
});

export default function ProjectDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [silOnay, setSilOnay] = useState(false);
  const qc = useQueryClient();

  const { data, isError } = useQuery({
    queryKey: ["project", id],
    queryFn: () => apiGet<ProjectDetailT>(`/projects/${id}`),
    retry: false,
    enabled: !!id,
  });

  const detail = isError ? null : data;
  const project = detail?.project;
  const stageList = useOptions("asama");
  const { can } = usePermissions();

  const [info, setInfo] = useState<ProjectPayload | null>(null);
  const [muh, setMuh] = useState<Muhasebe | null>(null);
  const [muhDirty, setMuhDirty] = useState(false);
  const [editItemId, setEditItemId] = useState<string | null>(null);
  const [item, setItem] = useState<ItemPayload>(emptyItem);
  const [crate, setCrate] = useState<CratePayload>(emptyCrate);
  const [itemOpen, setItemOpen] = useState(false);
  const [crateOpen, setCrateOpen] = useState(false);
  const [note, setNote] = useState("");
  const [dosya, setDosya] = useState<File | null>(null);
  const [kategori, setKategori] = useState("cizim");
  const [docAciklama, setDocAciklama] = useState("");
  const [revNote, setRevNote] = useState("");

  useEffect(() => {
    if (!project) return;
    const { id: _id, proje_kodu: _k, muhasebe, created_at: _c, updated_at: _u, kalem_sayisi: _n, ...rest } = project;
    setInfo(rest);
    setMuh((prev) => (muhDirty && prev ? prev : muhasebe));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["project", id] });
    qc.invalidateQueries({ queryKey: ["projects"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
    qc.invalidateQueries({ queryKey: ["alerts"] });
    qc.invalidateQueries({ queryKey: ["dealers"] });
    qc.invalidateQueries({ queryKey: ["documents", id] });
  };

  // ---- evraklar
  const { data: docs } = useQuery({
    queryKey: ["documents", id],
    queryFn: () => apiGet<DocumentMeta[]>(`/projects/${id}/evraklar`),
    retry: false,
    enabled: !!id && can("evrak:goruntule"),
  });

  const upload = useMutation({
    mutationFn: async () => {
      if (!dosya) throw new Error("no file");
      const body = new FormData();
      body.append("file", dosya);
      body.append("kategori", kategori);
      body.append("aciklama", docAciklama);
      const res = await fetch(`/api/projects/${id}/evraklar`, { method: "POST", body });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(
          (err as { detail?: string } | null)?.detail ?? "Evrak yüklenemedi",
        );
      }
      return res.json();
    },
    onSuccess: () => {
      invalidate();
      setDosya(null);
      setDocAciklama("");
      toast.success("Evrak yüklendi");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const delDoc = useMutation({
    mutationFn: (docId: string) => apiDelete(`/evraklar/${docId}`),
    onSuccess: () => {
      invalidate();
      toast.success("Evrak silindi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const silProje = useMutation({
    mutationFn: () => apiDelete(`/projects/${id}`),
    onSuccess: () => {
      toast.success("Proje kalıcı olarak silindi");
      navigate("/projeler", { replace: true });
    },
    onError: (e) => toast.error(errText(e)),
  });

  const crateLabels = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/projects/${id}/sandik-etiketleri`);
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error((err as { detail?: string } | null)?.detail ?? "Etiket oluşturulamadı");
      }
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `sandik-etiket-${project?.proje_kodu ?? id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    },
    onSuccess: () => toast.success("Sandık etiketleri indirildi"),
    onError: (e: Error) => toast.error(e.message),
  });

  const { data: revisions } = useQuery({
    queryKey: ["revisions", id],
    queryFn: () => apiGet<ProformaVersion[]>(`/projects/${id}/revizyonlar`),
    retry: false,
    enabled: !!id,
  });

  const saveRevision = useMutation({
    mutationFn: () => apiPost(`/projects/${id}/revizyonlar`, { aciklama: revNote }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["revisions", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
      setRevNote("");
      toast.success("Revizyon kaydedildi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const proforma = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/projects/${id}/proforma`);
      if (!res.ok) throw new Error("Proforma oluşturulamadı");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `proforma-${project?.proje_kodu ?? id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["revisions", id] });
      qc.invalidateQueries({ queryKey: ["project", id] });
      toast.success("Proforma PDF indirildi — Rev. kaydedildi");
    },
    onError: () => toast.error("Proforma oluşturulamadı"),
  });

  const stage = useMutation({
    mutationFn: (durum: string) => apiPatch(`/projects/${id}/stage`, { durum, not: "" }),
    onSuccess: () => {
      invalidate();
      toast.success("Aşama güncellendi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const saveInfo = useMutation({
    mutationFn: () => apiPut(`/projects/${id}`, info),
    onSuccess: () => {
      invalidate();
      toast.success("Proje bilgileri kaydedildi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const patchMuh = (patch: Partial<Muhasebe>) => {
    if (!muh) return;
    setMuhDirty(true);
    setMuh({ ...muh, ...patch });
  };

  const saveMuh = useMutation({
    mutationFn: () => apiPut(`/projects/${id}/muhasebe`, muh),
    onSuccess: () => {
      setMuhDirty(false);
      invalidate();
      toast.success("Muhasebe ve tahsilatlar kaydedildi, bakiye güncellendi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const addItem = useMutation({
    mutationFn: () => apiPost(`/projects/${id}/kalemler`, item),
    onSuccess: () => {
      invalidate();
      setItemOpen(false);
      setItem(emptyItem());
      toast.success("Kalem eklendi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const updateItem = useMutation({
    mutationFn: () => apiPut(`/kalemler/${editItemId}`, item),
    onSuccess: () => {
      invalidate();
      setItemOpen(false);
      setEditItemId(null);
      setItem(emptyItem());
      toast.success("Kalem güncellendi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const delItem = useMutation({
    mutationFn: (itemId: string) => apiDelete(`/kalemler/${itemId}`),
    onSuccess: () => {
      invalidate();
      toast.success("Kalem silindi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const addCrate = useMutation({
    mutationFn: () => apiPost(`/projects/${id}/sandiklar`, crate),
    onSuccess: () => {
      invalidate();
      setCrateOpen(false);
      setCrate(emptyCrate());
      toast.success("Sandık eklendi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const delCrate = useMutation({
    mutationFn: (crateId: string) => apiDelete(`/sandiklar/${crateId}`),
    onSuccess: () => {
      invalidate();
      toast.success("Sandık silindi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  const addNote = useMutation({
    mutationFn: () => apiPost(`/projects/${id}/notlar`, { mesaj: note }),
    onSuccess: () => {
      invalidate();
      setNote("");
      toast.success("Not eklendi");
    },
    onError: (e) => toast.error(errText(e)),
  });

  // Local mirrors of the backend's compute_muhasebe(), for instant feedback before save.
  const netSatis = (muh?.satis ?? 0) - (muh?.iskonto_tutari ?? 0);
  const toplamSatis = netSatis + (muh?.transfer_ucreti ?? 0);
  const netKar = netSatis - (muh?.alis ?? 0) - (muh?.transfer_ucreti ?? 0);
  const karYuzde = netSatis ? (netKar / netSatis) * 100 : 0;
  const tahsilat = (muh?.odemeler ?? []).reduce((s, o) => s + (Number(o.tutar) || 0), 0);
  const kalan = toplamSatis - tahsilat;
  const cur = project?.para_birimi ?? "";
  const toplamCbm = (detail?.sandiklar ?? []).reduce((s, c) => s + c.hacim_cbm, 0);
  const toplamKg = (detail?.sandiklar ?? []).reduce((s, c) => s + c.brut_kg, 0);
  const kalemToplam = (detail?.kalemler ?? []).reduce((s, k) => s + k.adet * k.birim_fiyat, 0);

  const num = (v: string) => (v === "" ? 0 : Number(v));
  const infoField = (key: keyof ProjectPayload, label: string, type = "text") => (
    <div className="space-y-1.5">
      <Label htmlFor={`f-${key}`}>{label}</Label>
      <Input
        id={`f-${key}`}
        type={type}
        value={(info?.[key] as string | null) ?? ""}
        onChange={(e) => info && setInfo({ ...info, [key]: e.target.value })}
        data-testid={`project-${String(key)}-input`}
      />
    </div>
  );

  if (isError) {
    return (
      <div data-testid="project-detail-page">
        <PageHeader title="Proje" subtitle="Kayıt yüklenemedi" />
        <EmptyState mesaj="Proje bulunamadı veya bağlantı kurulamadı." />
      </div>
    );
  }

  const activeIdx = stageList.findIndex((s) => s.deger === (project?.durum ?? ""));

  return (
    <div data-testid="project-detail-page">
      <PageHeader
        title={project?.proje_adi || "Proje Detayı"}
        subtitle={
          project
            ? `${project.proje_kodu} · ${project.musteri} · ${project.firma} · ${project.ulke}`
            : "Yükleniyor…"
        }
      >
        <Link to="/projeler" className={buttonVariants({ variant: "outline", size: "sm" })}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Projeler
        </Link>
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:text-destructive"
          disabled={!can("proje:sil")}
          onClick={() => setSilOnay(true)}
          data-testid="delete-project-button"
        >
          <Trash2 className="mr-2 h-4 w-4" /> Projeyi Sil
        </Button>
        <a
          href={`/api/projects/${id}/dosya.pdf`}
          target="_blank"
          rel="noreferrer"
          className={buttonVariants({ variant: "outline", size: "sm" })}
          data-testid="print-project-button"
        >
          <Printer className="mr-2 h-4 w-4" /> Proje ve Detaylarını Yazdır
        </a>
        <Button
          size="sm"
          onClick={() => proforma.mutate()}
          disabled={proforma.isPending || !can("proforma:olustur")}
          data-testid="proforma-download-button"
        >
          <FileDown className="mr-2 h-4 w-4" />
          {proforma.isPending ? "Hazırlanıyor…" : "Proforma PDF"}
        </Button>
        {project && <StageBadge durum={project.durum} />}
        {project && (
          <Badge variant="outline" className="font-mono">
            {SATIS_TIPLERI[project.satis_tipi] ?? project.satis_tipi} · {project.para_birimi}
          </Badge>
        )}
      </PageHeader>

      {/* 11-stage stepper */}
      <Card className="mb-6" data-testid="stage-stepper">
        <CardHeader>
          <CardTitle className="text-base">Süreç Aşaması — tıklayarak ilerletin</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {stageList.map((s, i) => {
              const done = i < activeIdx;
              const active = i === activeIdx;
              return (
                <button
                  key={s.deger}
                  type="button"
                  disabled={stage.isPending}
                  onClick={() => stage.mutate(s.deger)}
                  data-testid={`stage-step-${s.deger}`}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-transform duration-150 hover:-translate-y-0.5",
                    active && "animate-stage-pulse border-primary bg-primary/20 text-primary font-semibold",
                    done && "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
                    !active && !done && "border-border bg-secondary/40 text-muted-foreground",
                  )}
                >
                  {done && <Check className="h-3 w-3" />}
                  <span className="font-mono text-[10px]">{i + 1}</span>
                  {s.label}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="kalemler">
        <TabsList variant="line" className="mb-5 flex-wrap" data-testid="project-tabs">
          <TabsTrigger value="kalemler" data-testid="tab-kalemler">
            <Layers className="mr-2 h-4 w-4" /> Ürün Kalemleri
          </TabsTrigger>
          <TabsTrigger value="muhasebe" data-testid="tab-muhasebe">
            <CreditCard className="mr-2 h-4 w-4" /> Muhasebe & Tahsilat
          </TabsTrigger>
          <TabsTrigger value="lojistik" data-testid="tab-lojistik">
            <Package className="mr-2 h-4 w-4" /> Sandık & Sevkiyat
          </TabsTrigger>
          <TabsTrigger value="bilgiler" data-testid="tab-bilgiler">
            <FileText className="mr-2 h-4 w-4" /> Proje Bilgileri
          </TabsTrigger>
          <TabsTrigger value="evraklar" data-testid="tab-evraklar">
            <Paperclip className="mr-2 h-4 w-4" /> Evraklar ({docs?.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="gecmis" data-testid="tab-gecmis">
            <History className="mr-2 h-4 w-4" /> İşlem Geçmişi
          </TabsTrigger>
        </TabsList>

        {/* ---------- Items ---------- */}
        <TabsContent value="kalemler">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">
                Ürün Kalemleri ({detail?.kalemler.length ?? 0}) — Toplam{" "}
                <span className="font-mono text-primary">{fmtMoney(kalemToplam, cur)}</span>
              </CardTitle>
              <Dialog
                open={itemOpen}
                onOpenChange={(o: boolean) => {
                  setItemOpen(o);
                  if (!o) {
                    setEditItemId(null);
                    setItem(emptyItem());
                  }
                }}
              >
                <DialogTrigger
                  render={
                    <Button size="sm" data-testid="add-item-button" disabled={!can("kalem:yonet")}>
                      <Plus className="mr-2 h-4 w-4" /> Kalem Ekle
                    </Button>
                  }
                />
                <DialogContent className="max-h-[88vh] overflow-y-auto sm:max-w-3xl">
                  <DialogHeader>
                    <DialogTitle>{editItemId ? "Ürün Kalemini Düzenle" : "Yeni Ürün Kalemi"}</DialogTitle>
                  </DialogHeader>
                  <form
                    className="grid gap-4 sm:grid-cols-3"
                    data-testid="add-item-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (editItemId) updateItem.mutate();
                      else addItem.mutate();
                    }}
                  >
                    <CatalogSelect
                      tip="urun"
                      label="Ürün *"
                      value={item.urun}
                      onChange={(v) => setItem({ ...item, urun: v })}
                      testid="item-urun-select"
                      className="sm:col-span-3"
                    />
                    {(
                      [
                        ["adet", "Adet", "number"],
                        ["genislik_mm", "Genişlik (mm)", "number"],
                        ["acilim_mm", "Açılım (mm)", "number"],
                        ["aydinlatma_rengi", "Aydınlatma Rengi", "text"],
                        ["led_strip_mtul", "LED Strip (mtül)", "number"],
                        ["led_spot_adet", "LED Spot (adet)", "number"],
                        ["kumas_profil_rengi", "Kumaş Profil Rengi", "text"],
                        ["cam_olcusu", "Cam Ölçüsü", "text"],
                        ["birim_fiyat", "Birim Fiyat", "number"],
                      ] as [keyof ItemPayload, string, string][]
                    ).map(([key, label, type]) => (
                      <div className="space-y-1.5" key={key}>
                        <Label htmlFor={`i-${key}`}>{label}</Label>
                        <Input
                          id={`i-${key}`}
                          type={type}
                          value={String(item[key] ?? "")}
                          onChange={(e) =>
                            setItem({
                              ...item,
                              [key]: type === "number" ? num(e.target.value) : e.target.value,
                            })
                          }
                          data-testid={`item-${String(key)}-input`}
                        />
                      </div>
                    ))}
                    {(
                      [
                        ["yapi_rengi", "yapi_rengi", "Yapı Rengi (RAL)"],
                        ["panel_rengi", "panel_rengi", "Panel Rengi"],
                        ["aydinlatma", "aydinlatma", "Aydınlatma"],
                        ["zip_yapi_rengi", "yapi_rengi", "Zip Yapı Rengi"],
                        ["zip_kumasi", "kumas", "Zip Kumaşı"],
                        ["pergola_kumasi", "kumas", "Pergola Kumaşı"],
                        ["cam_rengi", "cam_rengi", "Cam Rengi"],
                        ["cam_kombinasyonu", "cam_kombinasyonu", "Cam Kombinasyonu"],
                        ["tedarikci", "tedarikci", "Tedarikçi"],
                      ] as [keyof ItemPayload, string, string][]
                    ).map(([key, tip, label]) => (
                      <CatalogSelect
                        key={key}
                        tip={tip}
                        label={label}
                        value={String(item[key] ?? "")}
                        onChange={(v) => setItem({ ...item, [key]: v })}
                        testid={`item-${String(key)}-select`}
                      />
                    ))}
                    <div className="space-y-1.5 sm:col-span-3">
                      <Label htmlFor="i-notlar">Not</Label>
                      <Textarea
                        id="i-notlar"
                        value={item.notlar}
                        onChange={(e) => setItem({ ...item, notlar: e.target.value })}
                        rows={2}
                        data-testid="item-notlar-input"
                      />
                    </div>
                    <DialogFooter className="sm:col-span-3">
                      <Button
                        type="submit"
                        disabled={addItem.isPending || updateItem.isPending}
                        data-testid="save-item-button"
                      >
                        {editItemId
                          ? updateItem.isPending
                            ? "Kaydediliyor…"
                            : "Kalemi Güncelle"
                          : addItem.isPending
                            ? "Ekleniyor…"
                            : "Kalemi Ekle"}
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {detail?.kalemler.length ? (
                <Table data-testid="items-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Ürün</TableHead>
                      <TableHead className="text-right">Adet</TableHead>
                      <TableHead className="text-right">Genişlik</TableHead>
                      <TableHead className="text-right">Açılım</TableHead>
                      <TableHead>Yapı / Panel Rengi</TableHead>
                      <TableHead>Aydınlatma</TableHead>
                      <TableHead>Cam / Kumaş</TableHead>
                      <TableHead>Tedarikçi</TableHead>
                      <TableHead className="text-right">Birim</TableHead>
                      <TableHead className="text-right">Tutar</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {detail.kalemler.map((k) => (
                      <TableRow
                        key={k.id}
                        className="transition-colors duration-100 hover:bg-secondary/50"
                        data-testid={`item-row-${k.id}`}
                      >
                        <TableCell className="max-w-64 text-sm">{k.urun}</TableCell>
                        <TableCell className="text-right font-mono text-xs">{k.adet}</TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {k.genislik_mm || "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {k.acilim_mm || "—"}
                        </TableCell>
                        <TableCell className="text-xs">
                          {k.yapi_rengi || "—"}
                          {k.panel_rengi ? ` / ${k.panel_rengi}` : ""}
                        </TableCell>
                        <TableCell className="text-xs">
                          {k.aydinlatma || "—"}
                          {k.led_strip_mtul ? ` · ${k.led_strip_mtul}m` : ""}
                          {k.led_spot_adet ? ` · ${k.led_spot_adet} spot` : ""}
                        </TableCell>
                        <TableCell className="max-w-48 text-xs">
                          {[k.cam_kombinasyonu, k.cam_rengi, k.zip_kumasi, k.pergola_kumasi]
                            .filter(Boolean)
                            .join(" · ") || "—"}
                        </TableCell>
                        <TableCell className="text-xs">{k.tedarikci || "—"}</TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {fmtMoney(k.birim_fiyat)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs font-semibold">
                          {fmtMoney(k.adet * k.birim_fiyat)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-0.5">
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              disabled={!can("kalem:yonet")}
                              onClick={() => {
                                const { id: _ki, proje_id: _kp, created_at: _kc, ...rest } = k;
                                setItem(rest as ItemPayload);
                                setEditItemId(k.id);
                                setItemOpen(true);
                              }}
                              data-testid={`edit-item-${k.id}`}
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              disabled={!can("kalem:yonet")}
                              onClick={() => delItem.mutate(k.id)}
                              data-testid={`delete-item-${k.id}`}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <EmptyState mesaj="Henüz kalem eklenmemiş." icon={<Layers className="h-6 w-6" />} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------- Accounting ---------- */}
        <TabsContent value="muhasebe">
          <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
            <Card data-testid="accounting-card">
              <CardHeader>
                <CardTitle className="text-base">Satış & Maliyet</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2">
                {(
                  [
                    ["satis", "Satış"],
                    ["alis", "Alış"],
                    ["iskonto_tutari", "İskonto Tutarı"],
                    ["transfer_ucreti", "Transfer Ücreti"],
                  ] as [keyof Muhasebe, string][]
                ).map(([key, label]) => (
                  <div className="space-y-1.5" key={key}>
                    <Label htmlFor={`m-${key}`}>{label}</Label>
                    <Input
                      id={`m-${key}`}
                      type="number"
                      step="0.01"
                      value={String(muh?.[key] ?? 0)}
                      onChange={(e) => patchMuh({ [key]: num(e.target.value) } as Partial<Muhasebe>)}
                      data-testid={`muhasebe-${String(key)}-input`}
                    />
                  </div>
                ))}
                <div className="space-y-1.5">
                  <Label>Fatura Tipi</Label>
                  <Select
                    value={muh?.fatura_tipi ?? "ihrac_kayitli"}
                    onValueChange={(v: string) => patchMuh({ fatura_tipi: v })}
                  >
                    <SelectTrigger data-testid="muhasebe-fatura_tipi-select">
                      <SelectValue>{(v) => FATURA_TIPLERI[v as string] ?? "—"}</SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(FATURA_TIPLERI).map(([k, v]) => (
                        <SelectItem key={k} value={k}>
                          {v}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Ödeme Durumu (otomatik)</Label>
                  <Input
                    readOnly
                    value={ODEME_DURUMLARI[muh?.odeme_durumu ?? "bekliyor"] ?? "—"}
                    data-testid="muhasebe-odeme_durumu-display"
                  />
                </div>

                <div className="sm:col-span-2 space-y-2 rounded-md border border-border bg-secondary/30 p-4">
                  {[
                    ["Transfer Dahil Toplam Satış", fmtMoney(toplamSatis, cur), "text-foreground", "calc-total-sales"],
                    ["Net Kar", fmtMoney(netKar, cur), netKar >= 0 ? "text-emerald-400" : "text-destructive", "calc-net-profit"],
                    ["Kar %", `${karYuzde.toFixed(2)} %`, "text-sky-400", "calc-margin"],
                    ["Toplam Tahsilat", fmtMoney(tahsilat, cur), "text-emerald-400", "calc-collected"],
                    ["Kalan Bakiye", fmtMoney(kalan, cur), kalan > 0 ? "text-amber-400" : "text-emerald-400", "calc-balance"],
                  ].map(([label, value, tone, testid]) => (
                    <div className="flex items-center justify-between" key={label} data-testid={testid}>
                      <span className="text-sm text-muted-foreground">{label}</span>
                      <span className={cn("font-mono text-sm font-semibold tabular-nums", tone)}>
                        {value}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="sm:col-span-2">
                  <Button
                    onClick={() => saveMuh.mutate()}
                    disabled={!can("muhasebe:duzenle") || saveMuh.isPending}
                    className="w-full"
                    data-testid="save-accounting-button"
                  >
                    <Save className="mr-2 h-4 w-4" />
                    {saveMuh.isPending ? "Kaydediliyor…" : "Muhasebeyi Kaydet"}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card data-testid="installments-card">
              <CardHeader>
                <CardTitle className="text-base">Alınan Ödemeler (5 Taksit)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {(muh?.odemeler ?? []).map((o, i) => (
                  <div
                    key={i}
                    className="grid gap-3 rounded-md border border-border p-3 sm:grid-cols-[auto_1fr_1fr]"
                    data-testid={`installment-row-${i + 1}`}
                  >
                    <Badge variant="secondary" className="h-fit font-mono">
                      {i + 1}. Ödeme
                    </Badge>
                    <div className="space-y-1.5">
                      <Label htmlFor={`o-t-${i}`}>Tutar</Label>
                      <Input
                        id={`o-t-${i}`}
                        type="number"
                        step="0.01"
                        value={String(o.tutar ?? 0)}
                        onChange={(e) => {
                          if (!muh) return;
                          patchMuh({
                            odemeler: muh.odemeler.map((x, xi) =>
                              xi === i ? { ...x, tutar: num(e.target.value) } : x,
                            ),
                          });
                        }}
                        data-testid={`installment-amount-${i + 1}`}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor={`o-d-${i}`}>Tahsilat Tarihi</Label>
                      <Input
                        id={`o-d-${i}`}
                        type="date"
                        value={o.tarih ?? ""}
                        onChange={(e) => {
                          if (!muh) return;
                          patchMuh({
                            odemeler: muh.odemeler.map((x, xi) =>
                              xi === i ? { ...x, tarih: e.target.value || null } : x,
                            ),
                          });
                        }}
                        data-testid={`installment-date-${i + 1}`}
                      />
                    </div>
                  </div>
                ))}
                {!muh && <EmptyState mesaj="Muhasebe verisi yükleniyor." />}

                <div className="space-y-2 rounded-md border border-border bg-secondary/30 p-4">
                  <div className="flex items-center justify-between" data-testid="pay-total-sales">
                    <span className="text-sm text-muted-foreground">Transfer Dahil Toplam Satış</span>
                    <span className="font-mono text-sm font-semibold tabular-nums">
                      {fmtMoney(toplamSatis, cur)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between" data-testid="pay-collected">
                    <span className="text-sm text-muted-foreground">Toplam Tahsilat</span>
                    <span className="font-mono text-sm font-semibold tabular-nums text-emerald-400">
                      {fmtMoney(tahsilat, cur)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between" data-testid="pay-balance">
                    <span className="text-sm text-muted-foreground">Kalan Bakiye</span>
                    <span
                      className={cn(
                        "font-mono text-sm font-semibold tabular-nums",
                        kalan > 0.009 ? "text-amber-400" : "text-emerald-400",
                      )}
                    >
                      {fmtMoney(kalan, cur)}
                    </span>
                  </div>
                </div>

                {muhDirty && (
                  <p className="text-xs text-amber-400" data-testid="pay-dirty-note">
                    Kaydedilmemiş değişiklik var — tahsilatların projeye yansıması için kaydedin.
                  </p>
                )}
                <Button
                  onClick={() => saveMuh.mutate()}
                  disabled={!can("muhasebe:duzenle") || saveMuh.isPending}
                  className="w-full"
                  data-testid="save-payments-button"
                >
                  <Save className="mr-2 h-4 w-4" />
                  {saveMuh.isPending ? "Kaydediliyor…" : "Tahsilatları Kaydet"}
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ---------- Logistics ---------- */}
        <TabsContent value="lojistik">
          <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
            <Card data-testid="crates-card">
              <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
                <CardTitle className="text-base">
                  Sandık / Paket Listesi — {toplamCbm.toFixed(3)} m³ · {toplamKg.toFixed(0)} kg
                </CardTitle>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => crateLabels.mutate()}
                  disabled={crateLabels.isPending || !can("proforma:olustur")}
                  data-testid="crate-labels-button"
                >
                  <Tags className="mr-2 h-4 w-4" />
                  {crateLabels.isPending ? "Hazırlanıyor…" : "Sandık Etiketi (A4/4)"}
                </Button>
                <Dialog open={crateOpen} onOpenChange={setCrateOpen}>
                  <DialogTrigger
                    render={
                      <Button size="sm" data-testid="add-crate-button" disabled={!can("sandik:yonet")}>
                        <Plus className="mr-2 h-4 w-4" /> Sandık Ekle
                      </Button>
                    }
                  />
                  <DialogContent className="sm:max-w-xl">
                    <DialogHeader>
                      <DialogTitle>Yeni Sandık / Paket</DialogTitle>
                    </DialogHeader>
                    <form
                      className="grid gap-4 sm:grid-cols-2"
                      data-testid="add-crate-form"
                      onSubmit={(e) => {
                        e.preventDefault();
                        addCrate.mutate();
                      }}
                    >
                      {(
                        [
                          ["sandik_no", "Sandık No", "text"],
                          ["taban_cm", "Taban / En (cm)", "number"],
                          ["uzunluk_cm", "Uzunluk (cm)", "number"],
                          ["yukseklik_cm", "Yükseklik (cm)", "number"],
                          ["adet", "Adet", "number"],
                          ["brut_kg", "Brüt Kilo (kg)", "number"],
                        ] as [keyof CratePayload, string, string][]
                      ).map(([key, label, type]) => (
                        <div className="space-y-1.5" key={key}>
                          <Label htmlFor={`c-${key}`}>{label}</Label>
                          <Input
                            id={`c-${key}`}
                            type={type}
                            value={String(crate[key] ?? "")}
                            onChange={(e) =>
                              setCrate({
                                ...crate,
                                [key]: type === "number" ? num(e.target.value) : e.target.value,
                              })
                            }
                            data-testid={`crate-${String(key)}-input`}
                          />
                        </div>
                      ))}
                      <CatalogSelect
                        tip="tedarikci"
                        label="Tedarikçi"
                        value={crate.tedarikci}
                        onChange={(v) => setCrate({ ...crate, tedarikci: v })}
                        testid="crate-tedarikci-select"
                      />
                      <div className="space-y-1.5 sm:col-span-2">
                        <Label htmlFor="c-icerik">İçerik</Label>
                        <Textarea
                          id="c-icerik"
                          rows={2}
                          value={crate.icerik}
                          onChange={(e) => setCrate({ ...crate, icerik: e.target.value })}
                          data-testid="crate-icerik-input"
                        />
                      </div>
                      <DialogFooter className="sm:col-span-2">
                        <Button
                          type="submit"
                          disabled={addCrate.isPending}
                          data-testid="save-crate-button"
                        >
                          {addCrate.isPending ? "Ekleniyor…" : "Sandığı Ekle"}
                        </Button>
                      </DialogFooter>
                    </form>
                  </DialogContent>
                </Dialog>
              </CardHeader>
              <CardContent>
                {detail?.sandiklar.length ? (
                  <Table data-testid="crates-table">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Sandık</TableHead>
                        <TableHead>İçerik</TableHead>
                        <TableHead className="text-right">Taban</TableHead>
                        <TableHead className="text-right">Uzunluk</TableHead>
                        <TableHead className="text-right">Yükseklik</TableHead>
                        <TableHead className="text-right">Adet</TableHead>
                        <TableHead className="text-right">m³</TableHead>
                        <TableHead className="text-right">Kg</TableHead>
                        <TableHead />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detail.sandiklar.map((c) => (
                        <TableRow key={c.id} data-testid={`crate-row-${c.id}`}>
                          <TableCell className="font-mono text-xs">{c.sandik_no || "—"}</TableCell>
                          <TableCell className="max-w-52 truncate text-xs">
                            {c.icerik || "—"}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">{c.taban_cm}</TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {c.uzunluk_cm}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {c.yukseklik_cm}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">{c.adet}</TableCell>
                          <TableCell className="text-right font-mono text-xs font-semibold text-primary">
                            {c.hacim_cbm}
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">{c.brut_kg}</TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => delCrate.mutate(c.id)}
                              data-testid={`delete-crate-${c.id}`}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <EmptyState
                    mesaj="Sandık listesi henüz girilmemiş."
                    icon={<Package className="h-6 w-6" />}
                  />
                )}
              </CardContent>
            </Card>

            <Card data-testid="shipping-info-card">
              <CardHeader>
                <CardTitle className="text-base">Lojistik, Fatura & Gümrük</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4">
                {infoField("lojistik_firmasi", "Lojistik Firması")}
                {infoField("rezervasyon_kodu", "Rezervasyon Kodu")}
                {infoField("konteyner_no", "Konteyner / Tır Plaka No")}
                {infoField("sevk_tarihi", "Sevk Tarihi", "date")}
                {infoField("gumruk_musavirligi", "Gümrük Müşavirliği")}
                {infoField("beyanname_no", "Beyanname No")}
                <Button
                  onClick={() => saveInfo.mutate()}
                  disabled={saveInfo.isPending || !can("proje:duzenle")}
                  data-testid="save-shipping-button"
                >
                  <Save className="mr-2 h-4 w-4" />
                  {saveInfo.isPending ? "Kaydediliyor…" : "Sevkiyat Bilgilerini Kaydet"}
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ---------- Project info ---------- */}
        <TabsContent value="bilgiler">
          <Card data-testid="project-info-card">
            <CardHeader>
              <CardTitle className="text-base">Proje Bilgileri</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <div className="space-y-1.5 sm:col-span-2 xl:col-span-3">
                <Label htmlFor="f-proje_adi">Proje Adı</Label>
                <Input
                  id="f-proje_adi"
                  value={info?.proje_adi ?? ""}
                  onChange={(e) => info && setInfo({ ...info, proje_adi: e.target.value })}
                  data-testid="project-proje_adi-input"
                />
              </div>
              {infoField("firma", "Firma")}
              {infoField("musteri", "Müşteri")}
              {infoField("ulke", "Ülke")}
              {infoField("tedarikci", "Tedarikçi")}
              {infoField("proje_tarihi", "Proje Tarihi", "date")}
              {infoField("termin_tarihi", "Termin Tarihi", "date")}
              {infoField("musteri_onay_tarihi", "Müşteri Onay Tarihi", "date")}
              {infoField("tedarikci_onay_tarihi", "Tedarikçi Onay Tarihi", "date")}

              <div className="space-y-1.5">
                <Label>Montaj Tipi</Label>
                <Select
                  value={info?.montaj_tipi || MONTAJ_TIPLERI[0]}
                  onValueChange={(v: string) => info && setInfo({ ...info, montaj_tipi: v })}
                >
                  <SelectTrigger data-testid="project-montaj_tipi-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MONTAJ_TIPLERI.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Para Birimi</Label>
                <Select
                  value={info?.para_birimi || "EUR"}
                  onValueChange={(v: string) => info && setInfo({ ...info, para_birimi: v })}
                >
                  <SelectTrigger data-testid="project-para_birimi-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PARA_BIRIMLERI.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Satış Tipi</Label>
                <Select
                  value={info?.satis_tipi || "ihracat"}
                  onValueChange={(v: string) => info && setInfo({ ...info, satis_tipi: v })}
                >
                  <SelectTrigger data-testid="project-satis_tipi-select">
                    <SelectValue>{(v) => SATIS_TIPLERI[v as string] ?? "—"}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(SATIS_TIPLERI).map(([k, v]) => (
                      <SelectItem key={k} value={k}>
                        {v}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5 sm:col-span-2 xl:col-span-3">
                <Label htmlFor="f-notlar">Not</Label>
                <Textarea
                  id="f-notlar"
                  rows={4}
                  value={info?.notlar ?? ""}
                  onChange={(e) => info && setInfo({ ...info, notlar: e.target.value })}
                  data-testid="project-notlar-input"
                />
              </div>
              <div className="sm:col-span-2 xl:col-span-3">
                <Button
                  onClick={() => saveInfo.mutate()}
                  disabled={saveInfo.isPending || !can("proje:duzenle")}
                  data-testid="save-info-button"
                >
                  <Save className="mr-2 h-4 w-4" />
                  {saveInfo.isPending ? "Kaydediliyor…" : "Bilgileri Kaydet"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------- Documents ---------- */}
        <TabsContent value="evraklar">
          <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
            <Card data-testid="documents-card">
              <CardHeader>
                <CardTitle className="text-base">
                  Proje Evrakları ({docs?.length ?? 0})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {docs?.length ? (
                  <Table data-testid="documents-table">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Dosya</TableHead>
                        <TableHead>Kategori</TableHead>
                        <TableHead className="text-right">Boyut</TableHead>
                        <TableHead>Yükleyen</TableHead>
                        <TableHead>Tarih</TableHead>
                        <TableHead className="text-right">İşlem</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {docs.map((d) => (
                        <TableRow
                          key={d.id}
                          className="transition-colors duration-100 hover:bg-secondary/50"
                          data-testid={`document-row-${d.id}`}
                        >
                          <TableCell className="max-w-64">
                            <p className="truncate text-sm">{d.dosya_adi}</p>
                            {d.aciklama && (
                              <p className="truncate text-xs text-muted-foreground">
                                {d.aciklama}
                              </p>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-[10px]">
                              {DOC_CATEGORIES[d.kategori] ?? d.kategori}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs">
                            {fmtBytes(d.boyut)}
                          </TableCell>
                          <TableCell className="text-xs">{d.yukleyen || "—"}</TableCell>
                          <TableCell className="font-mono text-xs">
                            {fmtDateTime(d.created_at)}
                          </TableCell>
                          <TableCell className="text-right">
                            <a
                              href={`/api/evraklar/${d.id}/goruntule`}
                              target="_blank"
                              rel="noreferrer"
                              title="Görüntüle / Yazdır"
                              className={buttonVariants({ variant: "ghost", size: "icon-sm" })}
                              data-testid={`print-document-${d.id}`}
                            >
                              <Printer className="h-4 w-4" />
                            </a>
                            <a
                              href={`/api/evraklar/${d.id}/indir`}
                              className={buttonVariants({ variant: "ghost", size: "icon-sm" })}
                              data-testid={`download-document-${d.id}`}
                            >
                              <Download className="h-4 w-4" />
                            </a>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => delDoc.mutate(d.id)}
                              data-testid={`delete-document-${d.id}`}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <EmptyState
                    mesaj="Henüz evrak yüklenmemiş. Çizim, paketleme listesi veya beyanname ekleyebilirsiniz."
                    icon={<Paperclip className="h-6 w-6" />}
                  />
                )}
              </CardContent>
            </Card>

            <Card data-testid="upload-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Upload className="h-4 w-4 text-primary" /> Evrak Yükle
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1.5">
                  <Label>Kategori</Label>
                  <Select value={kategori} onValueChange={(v: string) => setKategori(v)}>
                    <SelectTrigger data-testid="document-category-select">
                      <SelectValue>{(v) => DOC_CATEGORIES[v as string] ?? "Diğer"}</SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(DOC_CATEGORIES).map(([k, v]) => (
                        <SelectItem key={k} value={k}>
                          {v}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="doc-file">Dosya</Label>
                  <Input
                    id="doc-file"
                    type="file"
                    onChange={(e) => setDosya(e.target.files?.[0] ?? null)}
                    data-testid="document-file-input"
                  />
                  <p className="text-[11px] text-muted-foreground" data-testid="upload-hint">
                    En fazla 10 MB · PDF, resim, Excel, Word, DWG/DXF
                  </p>
                  <p className="text-[11px] text-primary" data-testid="drawing-proforma-hint">
                    "Çizim" kategorisindeki resimler (PNG/JPG) proforma PDF'inin sonunda
                    "Teknik Çizimler" sayfasına basılır.
                  </p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="doc-note">Açıklama</Label>
                  <Input
                    id="doc-note"
                    value={docAciklama}
                    onChange={(e) => setDocAciklama(e.target.value)}
                    placeholder="Rev.3 çizim, sandık listesi…"
                    data-testid="document-note-input"
                  />
                </div>
                <Button
                  className="w-full"
                  disabled={!dosya || upload.isPending || !can("evrak:yukle")}
                  onClick={() => upload.mutate()}
                  data-testid="upload-document-button"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  {upload.isPending ? "Yükleniyor…" : "Evrakı Yükle"}
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ---------- Timeline ---------- */}
        <TabsContent value="gecmis">
          <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
            <Card data-testid="timeline-card">
              <CardHeader>
                <CardTitle className="text-base">
                  İşlem Geçmişi ({detail?.hareketler.length ?? 0})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {detail?.hareketler.length ? (
                  detail.hareketler.map((a) => (
                    <div
                      key={a.id}
                      className="border-l-2 border-primary/40 pl-4"
                      data-testid={`timeline-item-${a.id}`}
                    >
                      <p className="text-sm">{a.mesaj}</p>
                      <p className="font-mono text-[11px] text-muted-foreground">
                        {a.tip} · {a.kullanici || "sistem"} · {fmtDateTime(a.created_at)}
                      </p>
                    </div>
                  ))
                ) : (
                  <EmptyState mesaj="Henüz hareket kaydı yok." />
                )}
              </CardContent>
            </Card>

            <div className="space-y-6">
              <Card data-testid="add-note-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <StickyNote className="h-4 w-4 text-primary" /> Not Ekle
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Textarea
                    rows={4}
                    placeholder="Revizyon detayı, müşteri görüşmesi, termin bilgisi…"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    data-testid="note-input"
                  />
                  <Button
                    className="w-full"
                    disabled={!note.trim() || addNote.isPending}
                    onClick={() => addNote.mutate()}
                    data-testid="add-note-button"
                  >
                    {addNote.isPending ? "Ekleniyor…" : "Notu Kaydet"}
                  </Button>
                </CardContent>
              </Card>

              <Card data-testid="revisions-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <GitCompare className="h-4 w-4 text-primary" /> Proforma Revizyonları (
                    {revisions?.length ?? 0})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Input
                    placeholder="Revizyon notu (ör. cam rengi değişti)"
                    value={revNote}
                    onChange={(e) => setRevNote(e.target.value)}
                    data-testid="revision-note-input"
                  />
                  <Button
                    className="w-full"
                    variant="outline"
                    disabled={saveRevision.isPending || !can("revizyon:yonet")}
                    onClick={() => saveRevision.mutate()}
                    data-testid="save-revision-button"
                  >
                    {saveRevision.isPending ? "Kaydediliyor…" : "Revizyon Kaydet"}
                  </Button>
                  {revisions?.length ? (
                    <div className="space-y-2">
                      {revisions.map((r, i) => {
                        const prev = revisions[i + 1];
                        const fark = prev ? r.toplam - prev.toplam : 0;
                        return (
                          <div
                            key={r.id}
                            className="rounded-md border border-border bg-secondary/30 p-2.5"
                            data-testid={`revision-row-${r.versiyon}`}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <Badge variant="secondary" className="font-mono text-[10px]">
                                Rev.{r.versiyon} {r.kaynak === "pdf" ? "· PDF" : ""}
                              </Badge>
                              <span className="font-mono text-xs font-semibold">
                                {fmtMoney(r.toplam, r.para_birimi)}
                              </span>
                            </div>
                            {!!prev && (
                              <p
                                className={`mt-1 font-mono text-[11px] ${fark > 0 ? "text-emerald-400" : fark < 0 ? "text-destructive" : "text-muted-foreground"}`}
                              >
                                Rev.{prev.versiyon} → Rev.{r.versiyon}:{" "}
                                {fark > 0 ? "+" : ""}
                                {fmtMoney(fark, r.para_birimi)} · kalem {prev.kalem_sayisi} →{" "}
                                {r.kalem_sayisi}
                              </p>
                            )}
                            <p className="mt-0.5 text-[11px] text-muted-foreground">
                              {r.aciklama || "—"} · {r.olusturan} · {fmtDateTime(r.created_at)}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Henüz revizyon yok. Proforma PDF aldığınızda otomatik kaydedilir.
                    </p>
                  )}
                </CardContent>
              </Card>

              <Card data-testid="milestones-card">
                <CardHeader>
                  <CardTitle className="text-base">Kilometre Taşları</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  {[
                    ["Proje Tarihi", project?.proje_tarihi],
                    ["Müşteri Onayı", project?.musteri_onay_tarihi],
                    ["Tedarikçi Onayı", project?.tedarikci_onay_tarihi],
                    ["Termin", project?.termin_tarihi],
                    ["Sevk", project?.sevk_tarihi],
                  ].map(([label, value]) => (
                    <div className="flex justify-between" key={label as string}>
                      <span className="text-muted-foreground">{label}</span>
                      <span className="font-mono text-xs">{fmtDate(value as string | null)}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={silOnay} onOpenChange={setSilOnay}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Projeyi Sil — {project?.proje_kodu}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4" data-testid="delete-project-dialog">
            <p className="text-sm text-muted-foreground">
              <b className="text-foreground">{project?.proje_adi}</b> projesi; ürün kalemleri,
              sandık kayıtları ve işlem geçmişiyle birlikte kalıcı olarak silinecek. Geri alınamaz —
              kaydı saklamak için silmek yerine <b>arşivleyin</b>.
            </p>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setSilOnay(false)}
                data-testid="delete-project-cancel-button"
              >
                Vazgeç
              </Button>
              <Button
                variant="destructive"
                disabled={silProje.isPending}
                onClick={() => silProje.mutate()}
                data-testid="delete-project-confirm-button"
              >
                {silProje.isPending ? "Siliniyor…" : "Kalıcı Olarak Sil"}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
