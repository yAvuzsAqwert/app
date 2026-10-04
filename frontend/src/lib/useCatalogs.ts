import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete, apiPatch, ApiError } from "@/lib/api";
import type { CatalogItem } from "@/lib/types";

export const CATALOG_LABELS: Record<string, string> = {
  asama: "Süreç Aşaması",
  urun: "Ürün",
  yapi_rengi: "Yapı Rengi",
  panel_rengi: "Panel Rengi",
  cam_kombinasyonu: "Cam Kombinasyonu",
  cam_rengi: "Cam Rengi",
  kumas: "Kumaş (Zip / Pergola)",
  aydinlatma: "Aydınlatma",
  montaj_tipi: "Montaj Tipi",
  firma: "Firma / Bayi",
  musteri: "Müşteri",
  tedarikci: "Tedarikçi",
  lojistik_firmasi: "Lojistik Firması",
  para_birimi: "Para Birimi",
  fatura_tipi: "Fatura Tipi",
};

export function useCatalog(tip: string) {
  const { data } = useQuery({
    queryKey: ["catalog", tip],
    queryFn: () => apiGet<CatalogItem[]>(`/catalogs/${tip}`),
    retry: false,
    staleTime: 60_000,
  });
  return data ?? [];
}

/** Aktif seçenekler — formlardaki açılır listeler için. */
export function useOptions(tip: string): CatalogItem[] {
  return useCatalog(tip).filter((c) => c.aktif);
}

export function catalogError(err: unknown, fallback = "İşlem başarısız oldu") {
  if (err instanceof ApiError) {
    const body = err.body as { detail?: unknown } | null;
    if (body && typeof body.detail === "string") return body.detail;
  }
  return fallback;
}

export function useCatalogMutations(tip: string, onDone?: () => void) {
  const qc = useQueryClient();
  const done = () => {
    qc.invalidateQueries({ queryKey: ["catalog", tip] });
    qc.invalidateQueries({ queryKey: ["projects"] });
    onDone?.();
  };
  return {
    create: useMutation({
      mutationFn: (label: string) => apiPost<CatalogItem>(`/catalogs/${tip}`, { label }),
      onSuccess: done,
    }),
    update: useMutation({
      mutationFn: (v: { id: string; label: string; aktif: boolean }) =>
        apiPut<CatalogItem>(`/catalogs/${tip}/${v.id}`, { label: v.label, aktif: v.aktif }),
      onSuccess: done,
    }),
    remove: useMutation({
      mutationFn: (id: string) => apiDelete(`/catalogs/${tip}/${id}`),
      onSuccess: done,
    }),
    reorder: useMutation({
      mutationFn: (ids: string[]) =>
        apiPatch<CatalogItem[]>(`/catalogs/${tip}/reorder`, { sirali_idler: ids }),
      onSuccess: done,
    }),
  };
}
