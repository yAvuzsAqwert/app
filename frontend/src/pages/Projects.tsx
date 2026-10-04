import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Search, Archive, ArchiveRestore, Trash2 } from "lucide-react";
import { apiGet, apiPatch, apiPost, apiDelete, ApiError } from "@/lib/api";
import type { BulkResult, DeadlineAlert, Project, ProjectPayload } from "@/lib/types";
import {
  ALERT_TONES,
  SATIS_TIPLERI,
  STAGES,
  alertText,
  fmtDate,
  fmtMoney,
} from "@/lib/constants";
import { PageHeader, EmptyState } from "@/components/AppShell";
import CatalogSelect from "@/components/CatalogSelect";
import { usePermissions } from "@/lib/usePermissions";
import { StageBadge } from "@/components/StageBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
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

const emptyProject = (): ProjectPayload => ({
  firma: "",
  musteri: "",
  ulke: "",
  proje_tarihi: new Date().toISOString().slice(0, 10),
  proje_adi: "",
  tedarikci: "",
  durum: "talep_alindi",
  arsiv: false,
  musteri_onay_tarihi: null,
  tedarikci_onay_tarihi: null,
  sevk_tarihi: null,
  termin_tarihi: null,
  montaj_tipi: "Duvara Montaj",
  para_birimi: "EUR",
  satis_tipi: "ihracat",
  lojistik_firmasi: "",
  rezervasyon_kodu: "",
  konteyner_no: "",
  gumruk_musavirligi: "",
  beyanname_no: "",
  notlar: "",
});

function errText(err: unknown) {
  if (err instanceof ApiError) {
    const body = err.body as { detail?: unknown } | null;
    if (body && typeof body.detail === "string") return body.detail;
  }
  return "İşlem başarısız oldu";
}

export default function Projects() {
  const qc = useQueryClient();
  const { can } = usePermissions();
  const [params, setParams] = useSearchParams();
  const durum = params.get("durum") ?? "";
  const gorunum = params.get("gorunum") ?? "aktif";
  const [arama, setArama] = useState("");
  const [open, setOpen] = useState(false);
  const [silFor, setSilFor] = useState<Project | null>(null);
  const [secili, setSecili] = useState<string[]>([]);
  const [topluSilOnay, setTopluSilOnay] = useState(false);
  const [form, setForm] = useState<ProjectPayload>(emptyProject);

  const query = useMemo(() => {
    const sp = new URLSearchParams();
    if (durum) sp.set("durum", durum);
    if (gorunum === "aktif") sp.set("arsiv", "false");
    if (gorunum === "arsiv") sp.set("arsiv", "true");
    if (arama.trim()) sp.set("q", arama.trim());
    const s = sp.toString();
    return s ? `/projects?${s}` : "/projects";
  }, [durum, gorunum, arama]);

  const { data, isError } = useQuery({
    queryKey: ["projects", query],
    queryFn: () => apiGet<Project[]>(query),
    retry: false,
  });
  const projects = isError ? [] : (data ?? []);

  // Termin/yükleme uyarıları: satırda rozet olarak gösterilir, sunucu hesaplar.
  const { data: alertData } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => apiGet<DeadlineAlert[]>("/alerts"),
    retry: false,
  });
  const alertByProject = new Map<string, DeadlineAlert>();
  for (const a of alertData ?? []) {
    const current = alertByProject.get(a.proje_id);
    if (!current || a.kalan_gun < current.kalan_gun) alertByProject.set(a.proje_id, a);
  }

  const create = useMutation({
    mutationFn: (payload: ProjectPayload) => apiPost<Project>("/projects", payload),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(`${p.proje_kodu} oluşturuldu`);
      setOpen(false);
      setForm(emptyProject());
    },
    onError: (err) => toast.error(errText(err)),
  });

  const archive = useMutation({
    mutationFn: (id: string) => apiPatch<Project>(`/projects/${id}/archive`),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(p.arsiv ? "Proje arşivlendi" : "Proje arşivden çıkarıldı");
    },
    onError: (err) => toast.error(errText(err)),
  });

  const sil = useMutation({
    mutationFn: (id: string) => apiDelete(`/projects/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      toast.success(`${silFor?.proje_kodu} kalıcı olarak silindi`);
      setSilFor(null);
    },
    onError: (err) => toast.error(errText(err)),
  });

  const bulkArchive = useMutation({
    mutationFn: (arsiv: boolean) =>
      apiPost<BulkResult>("/projects/bulk/archive", { ids: secili, arsiv }),
    onSuccess: (res, arsiv) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(
        `${res.etkilenen} proje ${arsiv ? "arşivlendi" : "arşivden çıkarıldı"}`,
      );
      setSecili([]);
    },
    onError: (err) => toast.error(errText(err)),
  });

  const bulkDelete = useMutation({
    mutationFn: () => apiPost<BulkResult>("/projects/bulk/delete", { ids: secili }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
      toast.success(`${res.etkilenen} proje kalıcı olarak silindi`);
      setSecili([]);
      setTopluSilOnay(false);
    },
    onError: (err) => toast.error(errText(err)),
  });

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const field = (key: keyof ProjectPayload, label: string, type = "text") => (
    <div className="space-y-1.5">
      <Label htmlFor={`new-${key}`}>{label}</Label>
      <Input
        id={`new-${key}`}
        type={type}
        value={(form[key] as string | null) ?? ""}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        data-testid={`new-project-${String(key)}-input`}
      />
    </div>
  );

  return (
    <div data-testid="projects-page">
      <PageHeader title="Projeler" subtitle="Tüm yurt içi ve ihracat projeleri">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger
            render={
              <Button data-testid="new-project-button" disabled={!can("proje:ekle")}>
                <Plus className="mr-2 h-4 w-4" /> Yeni Proje
              </Button>
            }
          />
          <DialogContent className="max-h-[88vh] overflow-y-auto sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>Yeni Proje Oluştur</DialogTitle>
            </DialogHeader>
            <form
              className="grid gap-4 sm:grid-cols-2"
              data-testid="new-project-form"
              onSubmit={(e) => {
                e.preventDefault();
                create.mutate(form);
              }}
            >
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="new-proje_adi">Proje Adı *</Label>
                <Input
                  id="new-proje_adi"
                  required
                  value={form.proje_adi}
                  onChange={(e) => setForm({ ...form, proje_adi: e.target.value })}
                  placeholder="Münih Restoran Terası — Bioklimatik Pergola"
                  data-testid="new-project-proje_adi-input"
                />
              </div>
              {field("ulke", "Ülke")}
              {field("proje_tarihi", "Proje Tarihi", "date")}
              {field("termin_tarihi", "Termin Tarihi", "date")}
              <CatalogSelect
                tip="firma"
                label="Firma / Bayi"
                value={form.firma}
                onChange={(v) => setForm({ ...form, firma: v })}
                testid="new-project-firma-select"
              />
              <CatalogSelect
                tip="musteri"
                label="Müşteri"
                value={form.musteri}
                onChange={(v) => setForm({ ...form, musteri: v })}
                testid="new-project-musteri-select"
              />
              <CatalogSelect
                tip="tedarikci"
                label="Tedarikçi"
                value={form.tedarikci}
                onChange={(v) => setForm({ ...form, tedarikci: v })}
                testid="new-project-tedarikci-select"
              />

              <div className="space-y-1.5">
                <Label>Başlangıç Aşaması</Label>
                <Select
                  value={form.durum}
                  onValueChange={(v: string) => setForm({ ...form, durum: v })}
                >
                  <SelectTrigger data-testid="new-project-durum-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STAGES.map((s) => (
                      <SelectItem key={s.key} value={s.key}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label>Satış Tipi</Label>
                <Select
                  value={form.satis_tipi}
                  onValueChange={(v: string) => setForm({ ...form, satis_tipi: v })}
                >
                  <SelectTrigger data-testid="new-project-satis_tipi-select">
                    <SelectValue />
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

              <CatalogSelect
                tip="para_birimi"
                label="Para Birimi"
                value={form.para_birimi}
                onChange={(v) => setForm({ ...form, para_birimi: v })}
                testid="new-project-para_birimi-select"
              />

              <CatalogSelect
                tip="montaj_tipi"
                label="Montaj Tipi"
                value={form.montaj_tipi}
                onChange={(v) => setForm({ ...form, montaj_tipi: v })}
                testid="new-project-montaj_tipi-select"
              />

              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="new-notlar">Not</Label>
                <Textarea
                  id="new-notlar"
                  value={form.notlar}
                  onChange={(e) => setForm({ ...form, notlar: e.target.value })}
                  rows={3}
                  data-testid="new-project-notlar-input"
                />
              </div>

              <DialogFooter className="sm:col-span-2">
                <Button type="submit" disabled={create.isPending} data-testid="save-project-button">
                  {create.isPending ? "Kaydediliyor…" : "Projeyi Kaydet"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </PageHeader>

      <Card className="mb-5">
        <CardContent className="flex flex-wrap items-center gap-3 pt-5">
          <div className="relative min-w-56 flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Proje kodu, müşteri, firma, ülke, konteyner no…"
              value={arama}
              onChange={(e) => setArama(e.target.value)}
              data-testid="project-search-input"
            />
          </div>
          <Select value={durum || "tumu"} onValueChange={(v: string) => setParam("durum", v === "tumu" ? "" : v)}>
            <SelectTrigger className="w-56" data-testid="filter-stage-select">
              <SelectValue>
                {(v) => (v === "tumu" ? "Tüm Aşamalar" : (STAGES.find((s) => s.key === v)?.label ?? "Tüm Aşamalar"))}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="tumu">Tüm Aşamalar</SelectItem>
              {STAGES.map((s) => (
                <SelectItem key={s.key} value={s.key}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={gorunum} onValueChange={(v: string) => setParam("gorunum", v)}>
            <SelectTrigger className="w-40" data-testid="filter-view-select">
              <SelectValue>
                {(v) => ({ aktif: "Aktif", arsiv: "Arşiv", tumu: "Tümü" })[v as string] ?? "Aktif"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="aktif">Aktif</SelectItem>
              <SelectItem value="arsiv">Arşiv</SelectItem>
              <SelectItem value="tumu">Tümü</SelectItem>
            </SelectContent>
          </Select>
          <Badge variant="outline" className="font-mono" data-testid="project-count-badge">
            {projects.length} kayıt
          </Badge>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-5">
          {secili.length > 0 && (
            <div
              className="mb-4 flex flex-wrap items-center gap-3 rounded-md border border-primary/40 bg-primary/10 p-3"
              data-testid="bulk-actions-bar"
            >
              <span className="text-sm">
                <b data-testid="bulk-selected-count">{secili.length}</b> proje seçildi
              </span>
              <Button
                variant="outline"
                size="sm"
                className="ml-auto"
                disabled={bulkArchive.isPending || !can("proje:sil")}
                onClick={() => bulkArchive.mutate(true)}
                data-testid="bulk-archive-button"
              >
                <Archive className="mr-2 h-4 w-4" /> Toplu Arşivle
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={bulkArchive.isPending || !can("proje:sil")}
                onClick={() => bulkArchive.mutate(false)}
                data-testid="bulk-unarchive-button"
              >
                <ArchiveRestore className="mr-2 h-4 w-4" /> Arşivden Çıkar
              </Button>
              <Button
                variant="destructive"
                size="sm"
                disabled={bulkDelete.isPending || !can("proje:sil")}
                onClick={() => setTopluSilOnay(true)}
                data-testid="bulk-delete-button"
              >
                <Trash2 className="mr-2 h-4 w-4" /> Toplu Sil
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSecili([])}
                data-testid="bulk-clear-button"
              >
                Seçimi Temizle
              </Button>
            </div>
          )}
          {projects.length ? (
            <Table data-testid="projects-table">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <Checkbox
                      checked={projects.length > 0 && secili.length === projects.length}
                      onCheckedChange={(v: boolean) =>
                        setSecili(v ? projects.map((p) => p.id) : [])
                      }
                      data-testid="select-all-projects"
                    />
                  </TableHead>
                  <TableHead>Proje Kodu</TableHead>
                  <TableHead>Proje / Müşteri</TableHead>
                  <TableHead>Ülke</TableHead>
                  <TableHead>Aşama</TableHead>
                  <TableHead>Tedarikçi</TableHead>
                  <TableHead className="text-right">Toplam Satış</TableHead>
                  <TableHead className="text-right">Kalan</TableHead>
                  <TableHead>Sevk / Termin</TableHead>
                  <TableHead className="text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projects.map((p) => (
                  <TableRow
                    key={p.id}
                    className="transition-colors duration-100 hover:bg-secondary/50"
                    data-testid={`project-row-${p.proje_kodu}`}
                  >
                    <TableCell className="w-10">
                      <Checkbox
                        checked={secili.includes(p.id)}
                        onCheckedChange={(v: boolean) =>
                          setSecili(v ? [...secili, p.id] : secili.filter((x) => x !== p.id))
                        }
                        data-testid={`select-project-${p.proje_kodu}`}
                      />
                    </TableCell>
                    <TableCell>
                      <Link
                        to={`/projeler/${p.id}`}
                        className="font-mono text-xs font-semibold text-sky-400 hover:underline"
                        data-testid={`project-link-${p.proje_kodu}`}
                      >
                        {p.proje_kodu}
                      </Link>
                      {p.arsiv && (
                        <Badge variant="secondary" className="ml-2 text-[10px]">
                          arşiv
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="max-w-72">
                      <p className="truncate text-sm">{p.proje_adi || "—"}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {p.musteri} · {p.firma}
                      </p>
                    </TableCell>
                    <TableCell className="text-sm">{p.ulke || "—"}</TableCell>
                    <TableCell>
                      <StageBadge durum={p.durum} />
                    </TableCell>
                    <TableCell className="text-sm">{p.tedarikci || "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {fmtMoney(p.muhasebe.transfer_dahil_toplam_satis, p.para_birimi)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      <span className={p.muhasebe.kalan_bakiye > 0 ? "text-amber-400" : "text-emerald-400"}>
                        {fmtMoney(p.muhasebe.kalan_bakiye, p.para_birimi)}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {fmtDate(p.sevk_tarihi ?? p.termin_tarihi)}
                      {alertByProject.has(p.id) && (
                        <span
                          className={`mt-1 block w-fit rounded-full border px-1.5 py-0.5 text-[10px] ${ALERT_TONES[alertByProject.get(p.id)!.seviye] ?? ""}`}
                          data-testid={`row-alert-${p.proje_kodu}`}
                        >
                          {alertText(alertByProject.get(p.id)!.kalan_gun)}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        title={p.arsiv ? "Arşivden çıkar" : "Arşivle"}
                        onClick={() => archive.mutate(p.id)}
                        data-testid={`archive-button-${p.proje_kodu}`}
                      >
                        {p.arsiv ? (
                          <ArchiveRestore className="h-4 w-4" />
                        ) : (
                          <Archive className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        title="Projeyi kalıcı olarak sil"
                        disabled={!can("proje:sil")}
                        onClick={() => setSilFor(p)}
                        data-testid={`delete-button-${p.proje_kodu}`}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyState mesaj="Bu filtrede proje bulunamadı. Yeni proje oluşturabilirsiniz." />
          )}
        </CardContent>
      </Card>

      <Dialog open={topluSilOnay} onOpenChange={setTopluSilOnay}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{secili.length} Projeyi Sil</DialogTitle>
          </DialogHeader>
          <div className="space-y-4" data-testid="bulk-delete-dialog">
            <p className="text-sm text-muted-foreground">
              Seçili <b className="text-foreground">{secili.length}</b> proje; ürün kalemleri,
              sandık kayıtları ve işlem geçmişiyle birlikte kalıcı olarak silinecek. Geri alınamaz —
              saklamak için <b>Toplu Arşivle</b>'yi kullanın.
            </p>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setTopluSilOnay(false)}
                data-testid="bulk-delete-cancel-button"
              >
                Vazgeç
              </Button>
              <Button
                variant="destructive"
                disabled={bulkDelete.isPending}
                onClick={() => bulkDelete.mutate()}
                data-testid="bulk-delete-confirm-button"
              >
                {bulkDelete.isPending ? "Siliniyor…" : "Kalıcı Olarak Sil"}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!silFor} onOpenChange={(o: boolean) => !o && setSilFor(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Projeyi Sil — {silFor?.proje_kodu}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4" data-testid="delete-project-dialog">
            <p className="text-sm text-muted-foreground">
              <b className="text-foreground">{silFor?.proje_adi}</b> projesi, ürün kalemleri,
              sandık kayıtları ve işlem geçmişiyle birlikte kalıcı olarak silinecek. Bu işlem geri
              alınamaz — kaydı saklamak isterseniz silmek yerine <b>arşivleyin</b>.
            </p>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setSilFor(null)}
                data-testid="delete-project-cancel-button"
              >
                Vazgeç
              </Button>
              <Button
                variant="destructive"
                disabled={sil.isPending}
                onClick={() => silFor && sil.mutate(silFor.id)}
                data-testid="delete-project-confirm-button"
              >
                {sil.isPending ? "Siliniyor…" : "Kalıcı Olarak Sil"}
              </Button>
            </DialogFooter>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
