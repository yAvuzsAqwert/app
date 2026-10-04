import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  TrendingUp,
  Wallet,
  HandCoins,
  Percent,
  Truck,
  Activity as ActivityIcon,
  FolderKanban,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";
import { fmtDate, fmtDateTime, fmtMoney, stageOf } from "@/lib/constants";
import { PageHeader, EmptyState } from "@/components/AppShell";
import { StageBadge } from "@/components/StageBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function Dashboard() {
  const { data, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiGet<DashboardStats>("/dashboard"),
    retry: false,
  });

  const stats = isError ? null : data;
  const maxStage = Math.max(1, ...(stats?.asamalar.map((a) => a.adet) ?? [1]));

  const kpis = [
    {
      label: "Toplam Satış Değeri",
      value: fmtMoney(stats?.toplam_satis ?? 0),
      icon: TrendingUp,
      tone: "text-primary",
      testid: "kpi-total-sales",
    },
    {
      label: "Tahsil Edilen",
      value: fmtMoney(stats?.toplam_tahsilat ?? 0),
      icon: HandCoins,
      tone: "text-emerald-400",
      testid: "kpi-collected",
    },
    {
      label: "Kalan Bakiye",
      value: fmtMoney(stats?.kalan_bakiye ?? 0),
      icon: Wallet,
      tone: "text-amber-400",
      testid: "kpi-balance",
    },
    {
      label: "Net Kar",
      value: fmtMoney(stats?.net_kar ?? 0),
      icon: TrendingUp,
      tone: "text-sky-400",
      testid: "kpi-profit",
    },
    {
      label: "Ortalama Kar %",
      value: `${(stats?.ortalama_kar_yuzdesi ?? 0).toFixed(2)} %`,
      icon: Percent,
      tone: "text-purple-400",
      testid: "kpi-margin",
    },
  ];

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        title="Komuta Paneli"
        subtitle="Tüm projelerin aşama, finans ve sevkiyat özeti"
      >
        <Badge variant="outline" className="font-mono" data-testid="dashboard-active-count">
          {stats?.aktif_proje ?? 0} aktif / {stats?.toplam_proje ?? 0} proje
        </Badge>
        <Link to="/projeler" className={buttonVariants({ variant: "default", size: "sm" })}>
          <FolderKanban className="mr-2 h-4 w-4" /> Projelere Git
        </Link>
      </PageHeader>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {kpis.map(({ label, value, icon: Icon, tone, testid }) => (
          <Card
            key={label}
            className="transition-transform duration-150 hover:-translate-y-0.5"
            data-testid={testid}
          >
            <CardContent className="pt-5">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
                <Icon className={`h-4 w-4 ${tone}`} />
              </div>
              <p className="font-mono text-xl font-semibold tabular-nums">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
        <Card data-testid="stage-distribution-card">
          <CardHeader>
            <CardTitle className="text-base">11 Aşamalı Süreç Dağılımı</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {(stats?.asamalar ?? []).map((a) => (
              <Link
                key={a.durum}
                to={`/projeler?durum=${a.durum}`}
                className="block rounded-md px-2 py-1.5 transition-colors duration-100 hover:bg-secondary/60"
                data-testid={`stage-row-${a.durum}`}
              >
                <div className="mb-1 flex items-baseline justify-between gap-3">
                  <span className="truncate text-sm">{a.label}</span>
                  <span className="shrink-0 font-mono text-xs text-muted-foreground">
                    {a.adet} proje · {fmtMoney(a.tutar)}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-500"
                    style={{ width: `${(a.adet / maxStage) * 100}%` }}
                  />
                </div>
              </Link>
            ))}
            {!stats && <EmptyState mesaj="Aşama verisi yüklenemedi." />}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card data-testid="upcoming-shipments-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Truck className="h-4 w-4 text-primary" /> Yaklaşan Sevkiyat / Termin
              </CardTitle>
            </CardHeader>
            <CardContent>
              {stats?.yaklasan_sevkiyatlar.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Proje</TableHead>
                      <TableHead>Aşama</TableHead>
                      <TableHead className="text-right">Tarih</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stats.yaklasan_sevkiyatlar.map((p) => (
                      <TableRow
                        key={p.id}
                        className="transition-colors duration-100 hover:bg-secondary/50"
                      >
                        <TableCell>
                          <Link
                            to={`/projeler/${p.id}`}
                            className="font-mono text-xs text-sky-400 hover:underline"
                            data-testid={`upcoming-link-${p.proje_kodu}`}
                          >
                            {p.proje_kodu}
                          </Link>
                          <p className="truncate text-xs text-muted-foreground">{p.musteri}</p>
                        </TableCell>
                        <TableCell>
                          <StageBadge durum={p.durum} />
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {fmtDate(p.sevk_tarihi ?? p.termin_tarihi)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <EmptyState mesaj="Planlanmış sevkiyat yok." icon={<Truck className="h-6 w-6" />} />
              )}
            </CardContent>
          </Card>

          <Card data-testid="recent-activity-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <ActivityIcon className="h-4 w-4 text-primary" /> Son Hareketler
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {stats?.son_hareketler.length ? (
                stats.son_hareketler.slice(0, 8).map((a) => (
                  <div
                    key={a.id}
                    className="flex gap-3 border-l-2 border-border pl-3"
                    data-testid={`activity-item-${a.id}`}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm">{a.mesaj}</p>
                      <p className="font-mono text-[11px] text-muted-foreground">
                        {a.proje_kodu} · {a.kullanici || "sistem"} · {fmtDateTime(a.created_at)}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState mesaj="Henüz hareket kaydı yok." />
              )}
            </CardContent>
          </Card>

          {!!stats?.para_birimi_dagilimi.length && (
            <Card data-testid="currency-card">
              <CardHeader>
                <CardTitle className="text-base">Para Birimi Dağılımı</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-3">
                {stats.para_birimi_dagilimi.map((c) => (
                  <div
                    key={c.durum}
                    className="rounded-md border border-border bg-secondary/40 p-3"
                    data-testid={`currency-${c.durum}`}
                  >
                    <p className="font-mono text-xs text-muted-foreground">
                      {stageOf(c.durum).key} · {c.adet} proje
                    </p>
                    <p className="font-mono text-sm font-semibold">{fmtMoney(c.tutar, c.label)}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
