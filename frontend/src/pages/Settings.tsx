import { useState } from "react";
import { toast } from "sonner";
import { ArrowDown, ArrowUp, Check, Pencil, Plus, Trash2, X, SlidersHorizontal } from "lucide-react";
import type { CatalogItem } from "@/lib/types";
import {
  CATALOG_LABELS,
  catalogError,
  useCatalog,
  useCatalogMutations,
} from "@/lib/useCatalogs";
import { PageHeader, EmptyState } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

const TYPES = Object.keys(CATALOG_LABELS);

export default function Settings() {
  const [tip, setTip] = useState("asama");
  const [yeni, setYeni] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");

  const rows = useCatalog(tip);
  const { create, update, remove, reorder } = useCatalogMutations(tip);
  const qcInvalidateStages = tip === "asama";
  void qcInvalidateStages;

  const ekle = () => {
    if (!yeni.trim()) return;
    create.mutate(yeni.trim(), {
      onSuccess: () => {
        toast.success("Tanım eklendi");
        setYeni("");
      },
      onError: (e) => toast.error(catalogError(e)),
    });
  };

  const kaydet = (row: CatalogItem) => {
    update.mutate(
      { id: row.id, label: editLabel.trim() || row.label, aktif: row.aktif },
      {
        onSuccess: () => {
          toast.success("Tanım güncellendi");
          setEditId(null);
        },
        onError: (e) => toast.error(catalogError(e)),
      },
    );
  };

  const durumDegistir = (row: CatalogItem) =>
    update.mutate(
      { id: row.id, label: row.label, aktif: !row.aktif },
      {
        onSuccess: () => toast.success(row.aktif ? "Pasife alındı" : "Aktif edildi"),
        onError: (e) => toast.error(catalogError(e)),
      },
    );

  const tasi = (index: number, yon: -1 | 1) => {
    const next = [...rows];
    const target = index + yon;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    reorder.mutate(next.map((r) => r.id), {
      onError: (e) => toast.error(catalogError(e)),
    });
  };

  const sil = (row: CatalogItem) =>
    remove.mutate(row.id, {
      onSuccess: () => toast.success("Tanım silindi"),
      onError: (e) => toast.error(catalogError(e, "Tanım silinemedi")),
    });

  return (
    <div data-testid="settings-page">
      <PageHeader
        title="Tanımlar"
        subtitle="Süreç aşamaları, ürünler, renkler, kumaşlar, firmalar ve tüm seçenek listeleri"
      >
        <Badge variant="outline" className="font-mono" data-testid="catalog-count-badge">
          {rows.length} kayıt
        </Badge>
      </PageHeader>

      <div className="grid gap-6 xl:grid-cols-[260px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <SlidersHorizontal className="h-4 w-4 text-primary" /> Liste Seç
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            <div className="xl:hidden">
              <Select value={tip} onValueChange={(v: string) => setTip(v)}>
                <SelectTrigger data-testid="catalog-type-select">
                  <SelectValue>{(v) => CATALOG_LABELS[v as string] ?? "Seç"}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {CATALOG_LABELS[t]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="hidden flex-col gap-1 xl:flex">
              {TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTip(t)}
                  data-testid={`catalog-tab-${t}`}
                  className={`rounded-md px-3 py-2 text-left text-sm transition-colors duration-150 ${
                    tip === t
                      ? "bg-primary/15 font-semibold text-primary"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  }`}
                >
                  {CATALOG_LABELS[t]}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{CATALOG_LABELS[tip]} Listesi</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder={`Yeni ${CATALOG_LABELS[tip].toLowerCase()} adı…`}
                value={yeni}
                onChange={(e) => setYeni(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && ekle()}
                data-testid="catalog-new-input"
              />
              <Button onClick={ekle} disabled={create.isPending} data-testid="catalog-add-button">
                <Plus className="mr-2 h-4 w-4" /> Ekle
              </Button>
            </div>

            {rows.length ? (
              <Table data-testid="catalog-table">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">Sıra</TableHead>
                    <TableHead>Ad</TableHead>
                    <TableHead>Durum</TableHead>
                    <TableHead className="text-right">Kullanım</TableHead>
                    <TableHead className="text-right">İşlem</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row, index) => (
                    <TableRow
                      key={row.id}
                      className="transition-colors duration-100 hover:bg-secondary/50"
                      data-testid={`catalog-row-${row.id}`}
                    >
                      <TableCell className="font-mono text-xs">{index + 1}</TableCell>
                      <TableCell>
                        {editId === row.id ? (
                          <Input
                            value={editLabel}
                            onChange={(e) => setEditLabel(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && kaydet(row)}
                            data-testid="catalog-edit-input"
                          />
                        ) : (
                          <span className="text-sm">{row.label}</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => durumDegistir(row)}
                          data-testid={`catalog-toggle-${row.id}`}
                        >
                          <Badge
                            variant="outline"
                            className={
                              row.aktif
                                ? "border-emerald-500/40 text-emerald-300"
                                : "border-border text-muted-foreground"
                            }
                          >
                            {row.aktif ? "Aktif" : "Pasif"}
                          </Badge>
                        </button>
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {row.kullanim}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-0.5">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => tasi(index, -1)}
                            data-testid={`catalog-up-${row.id}`}
                          >
                            <ArrowUp className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => tasi(index, 1)}
                            data-testid={`catalog-down-${row.id}`}
                          >
                            <ArrowDown className="h-3.5 w-3.5" />
                          </Button>
                          {editId === row.id ? (
                            <>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => kaydet(row)}
                                data-testid={`catalog-save-${row.id}`}
                              >
                                <Check className="h-4 w-4 text-emerald-400" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => setEditId(null)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </>
                          ) : (
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => {
                                setEditId(row.id);
                                setEditLabel(row.label);
                              }}
                              data-testid={`catalog-edit-${row.id}`}
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => sil(row)}
                            data-testid={`catalog-delete-${row.id}`}
                          >
                            <Trash2 className="h-3.5 w-3.5 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState mesaj="Bu listede kayıt yok. Yukarıdan ekleyebilirsiniz." />
            )}
            <p className="text-xs text-muted-foreground">
              Kullanımda olan bir tanım silinemez — "Pasif" yaparak yeni kayıtlarda
              görünmesini engelleyebilirsiniz.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
