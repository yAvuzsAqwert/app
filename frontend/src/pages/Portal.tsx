import { useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Sun, LogOut, ShieldCheck, FileText, Download, Image as ImageIcon } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import type { PortalSummary, PortalDocument } from "@/lib/types";
import { fmtDate, fmtMoney } from "@/lib/constants";
import { Button } from "@/components/ui/button";
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

const ODEME: Record<string, string> = {
  bekliyor: "Bekliyor",
  kismi: "Kısmi",
  tamamlandi: "Tamamlandı",
};

export default function Portal() {
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["portal", "ozet"],
    queryFn: () => apiGet<PortalSummary>("/portal/ozet"),
    retry: false,
  });

  const { data: docs } = useQuery({
    queryKey: ["portal", "evraklar"],
    queryFn: () => apiGet<PortalDocument[]>("/portal/evraklar"),
    retry: false,
  });

  const logout = useMutation({
    mutationFn: () => apiPost("/portal/logout"),
    onSuccess: () => navigate("/bayi-giris", { replace: true }),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          Yükleniyor…
        </p>
      </div>
    );
  }
  if (isError || !data) {
    navigate("/bayi-giris", { replace: true });
    return null;
  }

  const cur = data.para_birimi === "KARMA" ? "" : data.para_birimi;
  const kartlar: [string, string, string][] = [
    ["Toplam Sipariş", fmtMoney(data.toplam_satis, cur), "text-primary"],
    ["Tahsil Edilen", fmtMoney(data.toplam_tahsilat, cur), "text-emerald-400"],
    ["Açık Bakiye", fmtMoney(data.acik_bakiye, cur), "text-amber-400"],
  ];

  return (
    <div className="min-h-svh bg-background" data-testid="portal-page">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Sun className="h-5 w-5" />
          </div>
          <div>
            <p className="font-heading text-sm font-bold tracking-wide" data-testid="portal-firma">
              {data.firma}
            </p>
            <p className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
              Bayi Portalı · {data.ulke || "—"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="gap-1 font-mono text-[10px]">
            <ShieldCheck className="h-3 w-3" /> SALT OKUNUR
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={() => logout.mutate()}
            data-testid="portal-logout-button"
          >
            <LogOut className="mr-2 h-4 w-4" /> Çıkış
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          {kartlar.map(([baslik, deger, renk]) => (
            <Card key={baslik} data-testid={`portal-stat-${baslik}`}>
              <CardContent className="pt-5">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">{baslik}</p>
                <p className={`mt-1 font-mono text-xl font-semibold ${renk}`}>{deger}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card data-testid="portal-projects-card">
          <CardHeader>
            <CardTitle className="text-base">
              Projelerim ({data.proje_adet}) · {data.aktif_adet} aktif
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {data.projeler.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Proje Kodu</TableHead>
                    <TableHead>Proje / Müşteri</TableHead>
                    <TableHead>Aşama</TableHead>
                    <TableHead>Termin</TableHead>
                    <TableHead>Sevk</TableHead>
                    <TableHead className="text-right">Tutar</TableHead>
                    <TableHead className="text-right">Tahsilat</TableHead>
                    <TableHead className="text-right">Bakiye</TableHead>
                    <TableHead>Ödeme</TableHead>
                    <TableHead className="text-right">Evraklar</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.projeler.map((p) => (
                    <TableRow key={p.proje_kodu} data-testid={`portal-project-${p.proje_kodu}`}>
                      <TableCell className="font-mono text-xs text-primary">
                        {p.proje_kodu}
                      </TableCell>
                      <TableCell className="text-sm">
                        {p.proje_adi}
                        <span className="block text-xs text-muted-foreground">
                          {p.musteri || "—"}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-[10px]">
                          {p.durum_label}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {fmtDate(p.termin_tarihi)}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{fmtDate(p.sevk_tarihi)}</TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {fmtMoney(p.toplam_satis, p.para_birimi)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs text-emerald-400">
                        {fmtMoney(p.tahsilat, p.para_birimi)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs text-amber-400">
                        {fmtMoney(p.bakiye, p.para_birimi)}
                      </TableCell>
                      <TableCell className="text-xs">
                        {ODEME[p.odeme_durumu] ?? p.odeme_durumu}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const a = document.createElement("a");
                              a.href = `/api/portal/projeler/${encodeURIComponent(
                                p.proje_kodu,
                              )}/proforma`;
                              a.click();
                            }}
                            data-testid={`portal-proforma-${p.proje_kodu}`}
                          >
                            <FileText className="mr-1.5 h-3.5 w-3.5" /> Proforma
                          </Button>
                          {(docs ?? []).filter((d) => d.proje_kodu === p.proje_kodu).length ? (
                            <Badge
                              variant="secondary"
                              className="font-mono text-[10px]"
                              data-testid={`portal-doc-count-${p.proje_kodu}`}
                            >
                              {(docs ?? []).filter((d) => d.proje_kodu === p.proje_kodu).length}{" "}
                              çizim
                            </Badge>
                          ) : null}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Adınıza kayıtlı proje bulunmuyor.
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="mt-6" data-testid="portal-documents-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ImageIcon className="h-4 w-4 text-primary" /> Teknik Çizimlerim ({docs?.length ?? 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {docs?.length ? (
              docs.map((d) => (
                <div
                  key={d.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-secondary/20 p-3"
                  data-testid={`portal-doc-${d.id}`}
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm">{d.dosya_adi}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {d.proje_kodu} · {(d.boyut / 1024).toFixed(0)} KB ·{" "}
                      {d.aciklama || "açıklama yok"}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const a = document.createElement("a");
                      a.href = `/api/portal/evraklar/${d.id}/indir`;
                      a.click();
                    }}
                    data-testid={`portal-doc-download-${d.id}`}
                  >
                    <Download className="mr-1.5 h-3.5 w-3.5" /> İndir
                  </Button>
                </div>
              ))
            ) : (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Projelerinize yüklenmiş teknik çizim bulunmuyor.
              </p>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
