import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { History, Filter, RotateCcw } from "lucide-react";
import { apiGet } from "@/lib/api";
import type { Activity } from "@/lib/types";
import { fmtDateTime } from "@/lib/constants";
import { PageHeader, EmptyState } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

const TIPLER: Record<string, string> = {
  olusturma: "Oluşturma",
  asama: "Aşama değişimi",
  guncelleme: "Güncelleme",
  kalem: "Ürün kalemi",
  muhasebe: "Muhasebe",
  sandik: "Sandık",
  evrak: "Evrak",
  revizyon: "Revizyon",
  silme: "Silme",
  not: "Not",
};

const TUMU = "__all__";

export default function AuditLog() {
  const [kullanici, setKullanici] = useState(TUMU);
  const [tip, setTip] = useState(TUMU);
  const [baslangic, setBaslangic] = useState("");
  const [bitis, setBitis] = useState("");

  const { data: kullanicilar } = useQuery({
    queryKey: ["activity-users"],
    queryFn: () => apiGet<string[]>("/activities/kullanicilar"),
    retry: false,
  });

  const params = new URLSearchParams();
  if (kullanici !== TUMU) params.set("kullanici", kullanici);
  if (tip !== TUMU) params.set("tip", tip);
  if (baslangic) params.set("baslangic", baslangic);
  if (bitis) params.set("bitis", bitis);

  const { data: kayitlar, isLoading } = useQuery({
    queryKey: ["activities", params.toString()],
    queryFn: () => apiGet<Activity[]>(`/activities?${params.toString()}`),
    retry: false,
  });

  const sifirla = () => {
    setKullanici(TUMU);
    setTip(TUMU);
    setBaslangic("");
    setBitis("");
  };

  return (
    <div data-testid="audit-log-page">
      <PageHeader title="İşlem Günlüğü" subtitle="Kim, neyi, ne zaman değiştirdi veya sildi">
        <Badge variant="outline" className="font-mono" data-testid="audit-count-badge">
          {kayitlar?.length ?? 0} kayıt
        </Badge>
      </PageHeader>

      <Card className="mb-5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-normal text-muted-foreground">
            <Filter className="h-4 w-4" /> Filtreler
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <div className="space-y-1.5">
              <Label>Kullanıcı</Label>
              <Select value={kullanici} onValueChange={(v: string) => setKullanici(v)}>
                <SelectTrigger data-testid="audit-user-filter">
                  <SelectValue>
                    {(v) => ((v as string) === TUMU ? "Tüm kullanıcılar" : (v as string))}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TUMU}>Tüm kullanıcılar</SelectItem>
                  {(kullanicilar ?? []).map((k) => (
                    <SelectItem key={k} value={k}>
                      {k}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>İşlem Tipi</Label>
              <Select value={tip} onValueChange={(v: string) => setTip(v)}>
                <SelectTrigger data-testid="audit-type-filter">
                  <SelectValue>
                    {(v) =>
                      (v as string) === TUMU ? "Tüm işlemler" : (TIPLER[v as string] ?? (v as string))
                    }
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={TUMU}>Tüm işlemler</SelectItem>
                  {Object.entries(TIPLER).map(([k, v]) => (
                    <SelectItem key={k} value={k}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="a-bas">Başlangıç</Label>
              <Input
                id="a-bas"
                type="date"
                value={baslangic}
                onChange={(e) => setBaslangic(e.target.value)}
                data-testid="audit-start-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="a-bit">Bitiş</Label>
              <Input
                id="a-bit"
                type="date"
                value={bitis}
                onChange={(e) => setBitis(e.target.value)}
                data-testid="audit-end-input"
              />
            </div>
            <div className="flex items-end">
              <Button
                variant="outline"
                className="w-full"
                onClick={sifirla}
                data-testid="audit-reset-button"
              >
                <RotateCcw className="mr-2 h-4 w-4" /> Filtreleri Sıfırla
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="audit-table-card">
        <CardContent className="overflow-x-auto pt-5">
          {isLoading ? (
            <p className="py-8 text-center font-mono text-xs uppercase tracking-widest text-muted-foreground">
              Yükleniyor…
            </p>
          ) : kayitlar?.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tarih / Saat</TableHead>
                  <TableHead>Kullanıcı</TableHead>
                  <TableHead>İşlem</TableHead>
                  <TableHead>Proje</TableHead>
                  <TableHead>Açıklama</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {kayitlar.map((a) => (
                  <TableRow key={a.id} data-testid={`audit-row-${a.id}`}>
                    <TableCell className="whitespace-nowrap font-mono text-xs">
                      {fmtDateTime(a.created_at)}
                    </TableCell>
                    <TableCell className="text-sm">{a.kullanici || "—"}</TableCell>
                    <TableCell>
                      <Badge
                        variant={a.tip === "silme" ? "destructive" : "secondary"}
                        className="text-[10px]"
                      >
                        {TIPLER[a.tip] ?? a.tip}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {a.proje_kodu ? (
                        <Link
                          to={`/projeler/${a.proje_id}`}
                          className="text-sky-400 hover:underline"
                        >
                          {a.proje_kodu}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="max-w-[520px] text-sm">
                      {a.mesaj}
                      {a.eski_durum || a.yeni_durum ? (
                        <span className="block font-mono text-[11px] text-muted-foreground">
                          {a.eski_durum ?? "—"} → {a.yeni_durum ?? "—"}
                        </span>
                      ) : null}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <EmptyState
              mesaj="Bu filtrelerle kayıt bulunamadı."
              icon={<History className="h-6 w-6" />}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
