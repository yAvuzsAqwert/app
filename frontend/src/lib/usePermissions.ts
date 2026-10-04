import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { MyPermissions } from "@/lib/types";

/**
 * Oturumdaki kullanıcının rolü ve yetkileri. Sunucu her istekte yetkiyi yeniden
 * kontrol eder — buradaki `can()` yalnızca arayüzü sadeleştirmek içindir.
 */
export function usePermissions() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-permissions"],
    queryFn: () => apiGet<MyPermissions>("/my-permissions"),
    retry: false,
    staleTime: 30_000,
  });

  const yetkiler = data?.yetkiler ?? [];
  return {
    rol: data?.rol ?? "",
    rolLabel: data?.rol_label ?? "",
    yetkiler,
    loading: isLoading,
    can: (perm: string) => yetkiler.includes(perm),
  };
}
