import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Building2, ChevronDown, Search, Globe2 } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { DealerCard } from "@/lib/types";
import { fmtDate, fmtMoney } from "@/lib/constants";
import { PageHeader, EmptyState } from "@/components/AppShell";
import { StageBadge } from "@/components/StageBadge";
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
import { cn } from "@/lib/utils";

export default function Dealers() {
  const [arama, setArama] = useState("");
  const [acik, setAcik] = useState<string | null>(null);

  const { data, isError } = useQuery({
    queryKey: ["dealers"],
    queryFn: () => apiGet<DealerCard[]>("/dealers"),
    retry: false,
  });

  const dealers = (isError ? [] : (data ?? [])).filter((d) => {
    const q = arama.trim().toLowerCase();
    if (!q) return true;
    return (
      d.firma.toLowerCase().includes(q) ||
      d.ulke.toLowerCase().includes(q) ||
      d.musteriler.some((m) => m.toLowerCase().includes(q))
    );
  });

  const toplamCiro = dealers.reduce((s, d) => s + d.ciro, 0);
  const toplamAcik = dealers.reduce((s, d) => s + d.acik_bakiye, 0);

  return (
    <div data-testid="dealers-page">
      <PageHeader title="Bayi Kartları" subtitle="Firma + ülke bazında ciro, tahsilat ve açık bakiye">
        <Badge variant="outline" className="font-mono" data-testid="dealer-count-badge">
          {dealers.length} bayi
        </Badge>
      </PageHeader>

      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        <Card data-testid="dealer-total-revenue">
          <CardContent className="pt-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Toplam Ciro</p>
            <p className="mt-1 font-mono text-xl font-semibold text-primary">
              {fmtMoney(toplamCiro)}
            </p>
          </CardContent>
        </Card>
        <Card data-testid="dealer-total-open">
          <CardContent className="pt-5">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Toplam Açık Bakiye
            </p>
            <p className="mt-1 font-mono text-xl font-semibold text-amber-400">
              {fmtMoney(toplamAcik)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Firma, ülke veya müşteri ara…"
                value={arama}
                onChange={(e) => setArama(e.target.value)}
                data-testid="dealer-search-input"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {dealers.length ? (
        <div className="space-y-4">
          {dealers.map((d) => {
            const open = acik === d.anahtar;
            const tahsilOran = d.ciro ? (d.tahsilat / d.ciro) * 100 : 0;
            return (
              <Card
                key={d.anahtar}
                className="transition-transform duration-150 hover:-translate-y-0.5"
                data-testid={`dealer-card-${d.firma}`}
              >
                <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Building2 className="h-4 w-4 text-primary" />
                      {d.firma}
                      <Badge variant="secondary" className="gap-1 font-mono text-[10px]">
                        <Globe2 className="h-3 w-3" /> {d.ulke}
                      </Badge>
                    </CardTitle>
                    <p className="mt-1.5 text-xs text-muted-foreground">
                      {d.musteriler.join(", ") || "—"} · {d.proje_adet} proje ({d.aktif_adet} aktif
                      / {d.arsiv_adet} arşiv) · Son: {fmtDate(d.son_proje_tarihi)}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setAcik(open ? null : d.anahtar)}
                    data-testid={`dealer-toggle-${d.firma}`}
                  >
                    {open ? "Projeleri Gizle" : "Projeleri Göster"}
                    <ChevronDown
                      className={cn(
                        "ml-2 h-4 w-4 transition-transform duration-200",
                        open && "rotate-180",
                      )}
                    />
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                    {[
                      ["Ciro", fmtMoney(d.ciro, d.para_birimi), "text-primary"],
                      ["Tahsilat", fmtMoney(d.tahsilat, d.para_birimi), "text-emerald-400"],
                      [
                        "Açık Bakiye",
                        fmtMoney(d.acik_bakiye, d.para_birimi),
                        d.acik_bakiye > 0 ? "text-amber-400" : "text-emerald-400",
                      ],
                      ["Net Kar", fmtMoney(d.net_kar, d.para_birimi), "text-sky-400"],
                      ["Kar %", `${d.kar_yuzdesi.toFixed(2)} %`, "text-purple-400"],
                    ].map(([label, value, tone]) => (
                      <div
                        key={label}
                        className="rounded-md border border-border bg-secondary/30 p-3"
                        data-testid={`dealer-${d.firma}-${label}`}
                      >
                        <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                          {label}
                        </p>
                        <p className={cn("mt-0.5 font-mono text-sm font-semibold tabular-nums", tone)}>
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div>
                    <div className="mb-1.5 flex justify-between text-xs text-muted-foreground">
                      <span>Tahsilat oranı</span>
                      <span className="font-mono">{tahsilOran.toFixed(1)} %</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full bg-emerald-500 transition-[width] duration-500"
                        style={{ width: `${Math.min(100, Math.max(0, tahsilOran))}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {d.asama_dagilimi.map((a) => (
                      <Badge key={a.durum} variant="outline" className="font-mono text-[10px]">
                        {a.label}: {a.adet}
                      </Badge>
                    ))}
                  </div>

                  {open && (
                    <div className="animate-rise-in">
                      <Table data-testid={`dealer-projects-table-${d.firma}`}>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Proje Kodu</TableHead>
                            <TableHead>Proje</TableHead>
                            <TableHead>Aşama</TableHead>
                            <TableHead className="text-right">Toplam Satış</TableHead>
                            <TableHead className="text-right">Tahsilat</TableHead>
                            <TableHead className="text-right">Kalan</TableHead>
                            <TableHead>Sevk / Termin</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {d.projeler.map((p) => (
                            <TableRow key={p.id} className="hover:bg-secondary/50">
                              <TableCell>
                                <Link
                                  to={`/projeler/${p.id}`}
                                  className="font-mono text-xs text-sky-400 hover:underline"
                                  data-testid={`dealer-project-link-${p.proje_kodu}`}
                                >
                                  {p.proje_kodu}
                                </Link>
                              </TableCell>
                              <TableCell className="max-w-64 truncate text-sm">
                                {p.proje_adi}
                              </TableCell>
                              <TableCell>
                                <StageBadge durum={p.durum} />
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs">
                                {fmtMoney(p.muhasebe.transfer_dahil_toplam_satis, p.para_birimi)}
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs text-emerald-400">
                                {fmtMoney(p.muhasebe.toplam_tahsilat, p.para_birimi)}
                              </TableCell>
                              <TableCell className="text-right font-mono text-xs text-amber-400">
                                {fmtMoney(p.muhasebe.kalan_bakiye, p.para_birimi)}
                              </TableCell>
                              <TableCell className="font-mono text-xs">
                                {fmtDate(p.sevk_tarihi ?? p.termin_tarihi)}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <EmptyState
          mesaj="Bayi kaydı bulunamadı. Proje eklediğinizde bayiler otomatik oluşur."
          icon={<Building2 className="h-6 w-6" />}
        />
      )}
    </div>
  );
}
