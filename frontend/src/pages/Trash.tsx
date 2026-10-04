import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { apiGet, apiPost, apiDelete } from "@/lib/api";
import type { TrashItem } from "@/lib/types";
import { fmtDateTime } from "@/lib/constants";
import { PageHeader, EmptyState } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function Trash() {
  const qc = useQueryClient();
  const [silinecek, setSilinecek] = useState<TrashItem | null>(null);

  const { data: kayitlar, isLoading } = useQuery({
    queryKey: ["trash"],
    queryFn: () => apiGet<TrashItem[]>("/trash"),
    retry: false,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["trash"] });
    qc.invalidateQueries({ queryKey: ["projects"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const geriGetir = useMutation({
    mutationFn: (id: string) => apiPost<TrashItem>(`/trash/${id}/restore`, {}),
    onSuccess: (row) => {
      toast.success(`Proje geri getirildi: ${row.proje_kodu}`);
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Geri getirilemedi"),
  });

  const kaliciSil = useMutation({
    mutationFn: (id: string) => apiDelete<{ ok: boolean }>(`/trash/${id}`),
    onSuccess: () => {
      toast.success("Kayıt kalıcı olarak silindi");
      setSilinecek(null);
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message || "Silinemedi"),
  });

  return (
    <div data-testid="trash-page">
      <PageHeader
        title="Çöp Kutusu"
        subtitle="Silinen projeler 30 gün saklanır, bu süre içinde geri getirilebilir"
      >
        <Badge variant="outline" className="font-mono" data-testid="trash-count-badge">
          {kayitlar?.length ?? 0} kayıt
        </Badge>
      </PageHeader>

      <Card className="mt-6">
        <CardContent className="p-0">
          {isLoading ? (
            <p className="p-6 text-sm text-muted-foreground" data-testid="trash-loading">
              Yükleniyor...
            </p>
          ) : !kayitlar || kayitlar.length === 0 ? (
            <div className="p-6">
              <EmptyState mesaj="Çöp kutusu boş — silinen projeler burada 30 gün listelenir." />
            </div>
          ) : (
            <Table data-testid="trash-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Proje Kodu</TableHead>
                  <TableHead>Proje</TableHead>
                  <TableHead>Firma / Müşteri</TableHead>
                  <TableHead>Silinme</TableHead>
                  <TableHead>Kalan Süre</TableHead>
                  <TableHead>İçerik</TableHead>
                  <TableHead className="text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {kayitlar.map((k) => (
                  <TableRow key={k.id} data-testid={`trash-row-${k.proje_kodu}`}>
                    <TableCell className="font-mono text-xs">{k.proje_kodu}</TableCell>
                    <TableCell className="font-medium">{k.proje_adi}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {k.firma} / {k.musteri}
                    </TableCell>
                    <TableCell className="text-sm">
                      {fmtDateTime(k.silindi_at)}
                      {k.silen ? ` — ${k.silen}` : ""}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={k.kalan_gun <= 7 ? "destructive" : "secondary"}
                        data-testid={`trash-remaining-${k.proje_kodu}`}
                      >
                        {k.kalan_gun} gün
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {k.kalem_adet} kalem · {k.sandik_adet} sandık
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        className="mr-2"
                        disabled={geriGetir.isPending}
                        onClick={() => geriGetir.mutate(k.id)}
                        data-testid={`trash-restore-${k.proje_kodu}`}
                      >
                        <RotateCcw className="mr-2 h-4 w-4" /> Geri Getir
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSilinecek(k)}
                        data-testid={`trash-purge-${k.proje_kodu}`}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!silinecek} onOpenChange={(o) => !o && setSilinecek(null)}>
        <DialogContent className="sm:max-w-md" data-testid="trash-purge-dialog">
          <DialogHeader>
            <DialogTitle>Kalıcı olarak sil?</DialogTitle>
            <DialogDescription>
              {silinecek?.proje_kodu} — {silinecek?.proje_adi} kaydı kalıcı olarak silinecek. Bu
              işlem geri alınamaz.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSilinecek(null)} data-testid="trash-purge-cancel">
              Vazgeç
            </Button>
            <Button
              variant="destructive"
              disabled={kaliciSil.isPending}
              onClick={() => silinecek && kaliciSil.mutate(silinecek.id)}
              data-testid="trash-purge-confirm"
            >
              Kalıcı Sil
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
