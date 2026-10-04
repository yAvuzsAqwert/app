import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { CalendarDays, Coins, Download, TrendingUp } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { MonthlyReport as MonthlyReportT } from "@/lib/types";
import { fmtMoney } from "@/lib/constants";
import { PageHeader, EmptyState } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function MonthlyReport() {
  const [ay, setAy] = useState(() => new Date().toISOString().slice(0, 7));

  const { data, isError } = useQuery({
    queryKey: ["monthly", ay],
    queryFn: () => apiGet<MonthlyReportT>(`/reports/monthly?ay=${ay}`),
    retry: false,
  });
  const report = isError ? null : data;

  const download = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/reports/monthly/export?ay=${ay}`);
      if (!res.ok) throw new Error("export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pergola-aylik-${ay}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    },
    onSuccess: () => toast.success("Aylık rapor indirildi"),
    onError: () => toast.error("Aylık rapor oluşturulamadı"),
  });

  const kartlar: [string, number, string][] = [
    ["Ciro (TRY karşılığı)", report?.try_satis ?? 0, "text-primary"],
    ["Tahsilat (TRY)", report?.try_tahsilat ?? 0, "text-emerald-400"],
    ["Açık Bakiye (TRY)", report?.try_bakiye ?? 0, "text-amber-400"],
    ["Net Kar (TRY)", report?.try_net_kar ?? 0, "text-sky-400"],
  ];

  return (
    <div data-testid="monthly-report-page">
      <PageHeader title="Aylık Rapor" subtitle="Kur bazında ciro, tahsilat, kar + aşama ve bayi özeti">
        <Input
          type="month"
          className="w-44"
          value={ay}
          onChange={(e) => setAy(e.target.value)}
          data-testid="monthly-month-input"
        />
        <Badge variant="outline" className="font-mono" data-testid="monthly-project-count">
          {report?.proje_adet ?? 0} proje
        </Badge>
        <Button
          size="sm"
          onClick={() => download.mutate()}
          disabled={download.isPending}
          data-testid="monthly-export-button"
        >
          <Download className="mr-2 h-4 w-4" />
          {download.isPending ? "Hazırlanıyor…" : "Excel İndir"}
        </Button>
      </PageHeader>

      {report?.eksik_kurlar.length ? (
        <div
          className="mb-5 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-300"
          data-testid="monthly-missing-rates"
        >
          Kuru girilmemiş para birimi: <b>{report.eksik_kurlar.join(", ")}</b> — Tanımlar →
          Döviz Kurları ekranından girin, aksi halde TRY karşılığı 0 sayılır.
        </div>
      ) : null}

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kartlar.map(([label, value, tone]) => (
          <Card key={label} data-testid={`monthly-card-${label}`}>
            <CardContent className="pt-5">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>
                {fmtMoney(value, "TRY")}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card data-testid="monthly-currency-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Coins className="h-4 w-4 text-primary" /> Kur Bazında
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {report?.kur_dagilimi.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Para Birimi</TableHead>
                    <TableHead className="text-right">Proje</TableHead>
                    <TableHead className="text-right">Ciro</TableHead>
                    <TableHead className="text-right">Tahsilat</TableHead>
                    <TableHead className="text-right">Net Kar</TableHead>
                    <TableHead className="text-right">Kur</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.kur_dagilimi.map((c) => {
                    const kur =
                      c.para_birimi === "TRY"
                        ? 1
                        : (report.kurlar.find((k) => k.para_birimi === c.para_birimi)?.kur ?? 0);
                    return (
                      <TableRow key={c.para_birimi} data-testid={`monthly-currency-${c.para_birimi}`}>
                        <TableCell className="font-mono text-xs text-primary">
                          {c.para_birimi}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {c.proje_adet}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {fmtMoney(c.satis, c.para_birimi)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-emerald-400">
                          {fmtMoney(c.tahsilat, c.para_birimi)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-sky-400">
                          {fmtMoney(c.net_kar, c.para_birimi)}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-muted-foreground">
                          {kur ? `${kur.toFixed(4)} TRY` : "—"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            ) : (
              <EmptyState mesaj="Bu ayda proje bulunmuyor." icon={<CalendarDays className="h-6 w-6" />} />
            )}
          </CardContent>
        </Card>

        <Card data-testid="monthly-stage-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary" /> Aşama Özeti (TRY karşılığı)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {report?.asama_dagilimi.length ? (
              report.asama_dagilimi.map((a) => (
                <div
                  key={a.durum}
                  className="flex items-center justify-between gap-3 rounded-md border border-border bg-secondary/20 p-2.5"
                  data-testid={`monthly-stage-${a.durum}`}
                >
                  <span className="text-sm">{a.label}</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {a.adet} proje · {fmtMoney(a.tutar, "TRY")}
                  </span>
                </div>
              ))
            ) : (
              <EmptyState mesaj="Aşama verisi yok." />
            )}
          </CardContent>
        </Card>

        <Card className="xl:col-span-2" data-testid="monthly-dealer-card">
          <CardHeader>
            <CardTitle className="text-base">Bayi Özeti (TRY karşılığı)</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {report?.bayi_ozeti.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Firma</TableHead>
                    <TableHead>Ülke</TableHead>
                    <TableHead className="text-right">Proje</TableHead>
                    <TableHead className="text-right">Ciro (TRY)</TableHead>
                    <TableHead className="text-right">Tahsilat (TRY)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.bayi_ozeti.map((b) => (
                    <TableRow key={`${b.firma}-${b.ulke}`} data-testid={`monthly-dealer-${b.firma}`}>
                      <TableCell className="text-sm">{b.firma}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{b.ulke}</TableCell>
                      <TableCell className="text-right font-mono text-xs">{b.proje_adet}</TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {fmtMoney(b.satis_try, "TRY")}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs text-emerald-400">
                        {fmtMoney(b.tahsilat_try, "TRY")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState mesaj="Bu ayda bayi hareketi yok." />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
