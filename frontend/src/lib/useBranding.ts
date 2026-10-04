import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { Branding } from "@/lib/types";

/** Program adı, alt başlık ve logo — Tanımlar ekranından yönetilir. */
export function useBranding() {
  const { data } = useQuery({
    queryKey: ["branding"],
    queryFn: () => apiGet<Branding>("/branding"),
    retry: false,
    staleTime: 60_000,
  });
  return {
    programAdi: data?.program_adi ?? "PERGOLA TAKİP",
    altBaslik: data?.alt_baslik ?? "Tente & Cam Sistemleri",
    logoVar: data?.logo_var ?? false,
    logoUrl: "/api/branding/logo",
  };
}
