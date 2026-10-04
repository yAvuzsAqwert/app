import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  CalendarRange,
  ChevronLeft,
  ChevronRight,
  Coins,
  Download,
  FileSpreadsheet,
  GitCommitHorizontal,
  Truck,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import type { DailyReport as DailyReportT } from "@/lib/types";
import { fmtDate, fmtDateTime, fmtMoney } from "@/lib/constants";
import { PageHeader, EmptyState } from "@/components/AppShell";
import { StageBadge } from "@/components/StageBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const shiftDay = (iso: string, delta: number) => {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + delta);
  return d.toISOString().slice(0, 10);
};

export default function DailyReport() {
  const qc = useQueryClient();
  const [tarih, setTarih] = useState(() => new Date().toISOString().slice(0, 10));

  const { data, isError } = useQuery({
    queryKey: ["report", tarih],
    queryFn: () => apiGet<DailyReportT>(`/reports/daily?tarih=${tarih}`),
    retry: false,
  });
  const report = isError ? null : data;

  const download = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/reports/daily/export?tarih=${tarih}`);
      if (!res.ok) throw new Error("export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pergola-rapor-${tarih}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    },
    onSuccess: () => {
      toast.success("Excel raporu indirildi");
      qc.invalidateQueries({ queryKey: ["report", tarih] });
    },
    onError: () => toast.error("Excel raporu oluşturulamadı"),
  });

  const cards = [
    { label: "Yeni Proje", value: report?.yeni_projeler.length ?? 0, testid: "report-new-count" },
    {
      label: "Aşama Değişimi",
      value: report?.asama_degisimleri.length ?? 0,
      testid: "report-stage-count",
    },
    { label: "Sevk Edilen", value: report?.sevk_edilenler.length ?? 0, testid: "report-ship-count" },
    { label: "Aktif Proje", value: report?.aktif_proje ?? 0, testid: "report-active-count" },
  ];

  return (
    <div data-testid="report-page">
      <PageHeader title="Günlük Rapor" subtitle="Seçilen güne ait tüm süreç hareketleri">
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => setTarih(shiftDay(tarih, -1))}
          data-testid="report-prev-day-button"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Input
          type="date"
          className="w-40"
          value={tarih}
          onChange={(e) => setTarih(e.target.value)}
          data-testid="report-date-input"
        />
        <Button
          variant="outline"
          size="icon-sm"
          onClick={() => setTarih(shiftDay(tarih, 1))}
          data-testid="report-next-day-button"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setTarih(new Date().toISOString().slice(0, 10))}
          data-testid="report-today-button"
        >
          Bugün
        </Button>
        <Button
          size="sm"
          onClick={() => download.mutate()}
          disabled={download.isPending}
          data-testid="report-export-button"
        >
          <Download className="mr-2 h-4 w-4" />
          {download.isPending ? "Hazırlanıyor…" : "Excel (.xlsx) İndir"}
        </Button>
      </PageHeader>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((c) => (
          <Card key={c.label} data-testid={c.testid}>
            <CardContent className="pt-5">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{c.label}</p>
              <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">{c.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="mb-6 grid gap-4 sm:grid-cols-2">
        <Card data-testid="report-day-sales">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-normal uppercase tracking-wide text-muted-foreground">
              Gün İçinde Açılan Proje Değeri
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {report?.gun_satis_dagilimi.length ? (
              report.gun_satis_dagilimi.map((c) => (
                <div
                  key={c.para_birimi}
                  className="flex items-baseline justify-between gap-3"
                  data-testid={`report-day-sales-${c.para_birimi}`}
                >
                  <span className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
                    {c.para_birimi} · {c.proje_adet} proje
                  </span>
                  <span className="font-mono text-lg font-semibold text-primary">
                    {fmtMoney(c.satis, c.para_birimi)}
                  </span>
                </div>
              ))
            ) : (
              <p className="font-mono text-lg font-semibold text-muted-foreground">—</p>
            )}
          </CardContent>
        </Card>
        <Card data-testid="report-day-collection">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-normal uppercase tracking-wide text-muted-foreground">
              Sevk Edilen Projelerin Tahsilatı
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {report?.gun_tahsilat_dagilimi.length ? (
              report.gun_tahsilat_dagilimi.map((c) => (
                <div
                  key={c.para_birimi}
                  className="flex items-baseline justify-between gap-3"
                  data-testid={`report-day-collection-${c.para_birimi}`}
                >
                  <span className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
                    {c.para_birimi} · {c.proje_adet} proje
                  </span>
                  <span className="font-mono text-lg font-semibold text-emerald-400">
                    {fmtMoney(c.tahsilat, c.para_birimi)}
                  </span>
                </div>
              ))
            ) : (
              <p className="font-mono text-lg font-semibold text-muted-foreground">—</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Para birimi kırılımı — farklı kurlar asla tek toplamda birleştirilmez */}
      <Card className="mb-6" data-testid="report-currency-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Coins className="h-4 w-4 text-primary" /> Para Birimine Göre Kırılım (tüm aktif
            projeler)
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {report?.genel_dagilim.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Para Birimi</TableHead>
                  <TableHead className="text-right">Proje</TableHead>
                  <TableHead className="text-right">Toplam Satış</TableHead>
                  <TableHead className="text-right">Tahsilat</TableHead>
                  <TableHead className="text-right">Kalan Bakiye</TableHead>
                  <TableHead className="text-right">Net Kar</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {report.genel_dagilim.map((c) => (
                  <TableRow key={c.para_birimi} data-testid={`report-currency-${c.para_birimi}`}>
                    <TableCell className="font-mono text-xs text-primary">
                      {c.para_birimi}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">{c.proje_adet}</TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {fmtMoney(c.satis, c.para_birimi)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-emerald-400">
                      {fmtMoney(c.tahsilat, c.para_birimi)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-amber-400">
                      {fmtMoney(c.bakiye, c.para_birimi)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-sky-400">
                      {fmtMoney(c.net_kar, c.para_birimi)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyState mesaj="Aktif proje bulunmuyor." />
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_1fr]">
        <Card data-testid="report-activity-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <GitCommitHorizontal className="h-4 w-4 text-primary" /> {fmtDate(tarih)} Hareketleri
            </CardTitle>
          </CardHeader>
          <CardContent>
            {report?.tum_hareketler.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Saat</TableHead>
                    <TableHead>Proje</TableHead>
                    <TableHead>Açıklama</TableHead>
                    <TableHead>Kullanıcı</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.tum_hareketler.map((a) => (
                    <TableRow key={a.id} data-testid={`report-activity-${a.id}`}>
                      <TableCell className="font-mono text-xs">
                        {new Date(a.created_at).toLocaleTimeString("tr-TR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-sky-400">
                        {a.proje_kodu}
                      </TableCell>
                      <TableCell className="text-sm">{a.mesaj}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {a.kullanici || "sistem"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState
                mesaj="Bu tarihte kayıtlı hareket yok."
                icon={<CalendarRange className="h-6 w-6" />}
              />
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card data-testid="report-new-projects-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileSpreadsheet className="h-4 w-4 text-primary" /> Gün İçinde Açılan Projeler
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {report?.yeni_projeler.length ? (
                report.yeni_projeler.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between gap-3 rounded-md border border-border bg-secondary/30 p-3"
                    data-testid={`report-new-project-${p.proje_kodu}`}
                  >
                    <div className="min-w-0">
                      <p className="font-mono text-xs text-sky-400">{p.proje_kodu}</p>
                      <p className="truncate text-sm">{p.proje_adi}</p>
                    </div>
                    <StageBadge durum={p.durum} />
                  </div>
                ))
              ) : (
                <EmptyState mesaj="Bu tarihte yeni proje açılmamış." />
              )}
            </CardContent>
          </Card>

          <Card data-testid="report-shipped-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Truck className="h-4 w-4 text-primary" /> Sevk Edilenler
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {report?.sevk_edilenler.length ? (
                report.sevk_edilenler.map((p) => (
                  <div
                    key={p.id}
                    className="rounded-md border border-border bg-secondary/30 p-3"
                    data-testid={`report-shipped-${p.proje_kodu}`}
                  >
                    <p className="font-mono text-xs text-sky-400">{p.proje_kodu}</p>
                    <p className="truncate text-sm">{p.proje_adi}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {p.lojistik_firmasi || "—"} · {p.konteyner_no || "—"} ·{" "}
                      {fmtDateTime(p.updated_at)}
                    </p>
                  </div>
                ))
              ) : (
                <EmptyState mesaj="Bu tarihte sevkiyat yok." />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
