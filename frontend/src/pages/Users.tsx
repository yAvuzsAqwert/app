import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ShieldCheck, UserPlus, Trash2, Users as UsersIcon, Save, KeyRound } from "lucide-react";
import { apiGet, apiPost, apiPut, apiDelete, ApiError } from "@/lib/api";
import type { Role, UserAccount } from "@/lib/types";
import { fmtDate } from "@/lib/constants";
import { PageHeader } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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

function errText(err: unknown, fallback = "İşlem başarısız oldu") {
  if (err instanceof ApiError) {
    const body = err.body as { detail?: unknown } | null;
    if (body && typeof body.detail === "string") return body.detail;
  }
  return fallback;
}

export default function Users() {
  const qc = useQueryClient();
  const [secili, setSecili] = useState("satis");
  const [taslak, setTaslak] = useState<string[] | null>(null);
  const [yeni, setYeni] = useState({ email: "", sifre: "", ad_soyad: "", rol: "satis" });
  const [resetFor, setResetFor] = useState<UserAccount | null>(null);
  const [yeniSifre, setYeniSifre] = useState("");

  const { data: perms } = useQuery({
    queryKey: ["permission-catalog"],
    queryFn: () => apiGet<Record<string, string>>("/permissions"),
    retry: false,
  });
  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: () => apiGet<Role[]>("/roles"),
    retry: false,
  });
  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => apiGet<UserAccount[]>("/users"),
    retry: false,
  });

  const rol = (roles ?? []).find((r) => r.kod === secili);
  const aktifYetkiler = taslak ?? rol?.yetkiler ?? [];
  const roleLabel = (kod: string) => (roles ?? []).find((r) => r.kod === kod)?.label ?? kod;

  const saveRole = useMutation({
    mutationFn: () => apiPut<Role>(`/roles/${secili}`, { yetkiler: aktifYetkiler }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles"] });
      qc.invalidateQueries({ queryKey: ["my-permissions"] });
      setTaslak(null);
      toast.success("Rol yetkileri kaydedildi");
    },
    onError: (e) => toast.error(errText(e, "Yetkiler kaydedilemedi")),
  });

  const createUser = useMutation({
    mutationFn: () => apiPost<UserAccount>("/users", yeni),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setYeni({ email: "", sifre: "", ad_soyad: "", rol: "satis" });
      toast.success("Kullanıcı oluşturuldu");
    },
    onError: (e) => toast.error(errText(e, "Kullanıcı oluşturulamadı")),
  });

  const setRole = useMutation({
    mutationFn: (v: { id: string; rol: string }) => apiPut(`/users/${v.id}/rol`, { rol: v.rol }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      qc.invalidateQueries({ queryKey: ["my-permissions"] });
      toast.success("Rol güncellendi");
    },
    onError: (e) => toast.error(errText(e, "Rol güncellenemedi")),
  });

  const removeUser = useMutation({    mutationFn: (id: string) => apiDelete(`/users/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("Kullanıcı silindi");
    },
    onError: (e) => toast.error(errText(e, "Kullanıcı silinemedi")),
  });

  const resetPassword = useMutation({
    mutationFn: () => apiPut(`/users/${resetFor?.id}/sifre`, { yeni_sifre: yeniSifre }),
    onSuccess: () => {
      toast.success(`${resetFor?.email} şifresi sıfırlandı`);
      setResetFor(null);
      setYeniSifre("");
    },
    onError: (e) => toast.error(errText(e, "Şifre sıfırlanamadı")),
  });

  const toggle = (kod: string) =>
    setTaslak(
      aktifYetkiler.includes(kod)
        ? aktifYetkiler.filter((y) => y !== kod)
        : [...aktifYetkiler, kod],
    );

  return (
    <div data-testid="users-page">
      <PageHeader
        title="Kullanıcılar & Yetkiler"
        subtitle="Rolleri görevlere göre düzenleyin, kullanıcıları rollere atayın"
      >
        <Badge variant="outline" className="font-mono" data-testid="user-count-badge">
          {users?.length ?? 0} kullanıcı
        </Badge>
      </PageHeader>

      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <div className="space-y-6">
          <Card data-testid="users-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <UsersIcon className="h-4 w-4 text-primary" /> Kullanıcılar
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ad Soyad</TableHead>
                    <TableHead>E-posta</TableHead>
                    <TableHead>Rol</TableHead>
                    <TableHead>Kayıt</TableHead>
                    <TableHead className="text-right">İşlem</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(users ?? []).map((u) => (
                    <TableRow key={u.id} data-testid={`user-row-${u.email}`}>
                      <TableCell className="text-sm">{u.ad_soyad}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {u.email}
                      </TableCell>
                      <TableCell>
                        <Select
                          value={u.rol}
                          onValueChange={(v: string) => setRole.mutate({ id: u.id, rol: v })}
                        >
                          <SelectTrigger
                            className="h-8 w-44"
                            data-testid={`user-role-select-${u.email}`}
                          >
                            <SelectValue>{(v) => roleLabel(v as string)}</SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {(roles ?? []).map((r) => (
                              <SelectItem key={r.kod} value={r.kod}>
                                {r.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{fmtDate(u.created_at)}</TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            title="Şifre sıfırla"
                            onClick={() => {
                              setResetFor(u);
                              setYeniSifre("");
                            }}
                            data-testid={`user-reset-password-${u.email}`}
                          >
                            <KeyRound className="h-4 w-4 text-primary" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => removeUser.mutate(u.id)}
                            data-testid={`user-delete-${u.email}`}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card data-testid="role-permissions-card">
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldCheck className="h-4 w-4 text-primary" /> Rol Yetkileri
              </CardTitle>
              <div className="flex items-center gap-2">
                <Select
                  value={secili}
                  onValueChange={(v: string) => {
                    setSecili(v);
                    setTaslak(null);
                  }}
                >
                  <SelectTrigger className="w-52" data-testid="role-select">
                    <SelectValue>{(v) => roleLabel(v as string)}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {(roles ?? []).map((r) => (
                      <SelectItem key={r.kod} value={r.kod}>
                        {r.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  size="sm"
                  disabled={secili === "admin" || saveRole.isPending || !taslak}
                  onClick={() => saveRole.mutate()}
                  data-testid="role-save-button"
                >
                  <Save className="mr-2 h-4 w-4" />
                  {saveRole.isPending ? "Kaydediliyor…" : "Kaydet"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {secili === "admin" && (
                <p className="mb-3 text-xs text-amber-400" data-testid="admin-role-note">
                  Admin rolü daima tüm yetkilere sahiptir ve değiştirilemez.
                </p>
              )}
              <div className="grid gap-2 sm:grid-cols-2">
                {Object.entries(perms ?? {}).map(([kod, label]) => (
                  <label
                    key={kod}
                    className="flex items-center gap-2.5 rounded-md border border-border bg-secondary/20 p-2.5 text-sm transition-colors duration-150 hover:border-primary/40"
                    data-testid={`perm-${kod}`}
                  >
                    <Checkbox
                      checked={aktifYetkiler.includes(kod)}
                      disabled={secili === "admin"}
                      onCheckedChange={() => toggle(kod)}
                      data-testid={`perm-checkbox-${kod}`}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="h-fit" data-testid="new-user-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UserPlus className="h-4 w-4 text-primary" /> Yeni Kullanıcı
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              data-testid="new-user-form"
              onSubmit={(e) => {
                e.preventDefault();
                createUser.mutate();
              }}
            >
              <div className="space-y-1.5">
                <Label htmlFor="nu-ad">Ad Soyad</Label>
                <Input
                  id="nu-ad"
                  required
                  value={yeni.ad_soyad}
                  onChange={(e) => setYeni({ ...yeni, ad_soyad: e.target.value })}
                  data-testid="new-user-name-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="nu-email">E-posta</Label>
                <Input
                  id="nu-email"
                  type="email"
                  required
                  value={yeni.email}
                  onChange={(e) => setYeni({ ...yeni, email: e.target.value })}
                  data-testid="new-user-email-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="nu-sifre">Şifre (en az 6 karakter)</Label>
                <Input
                  id="nu-sifre"
                  required
                  minLength={6}
                  value={yeni.sifre}
                  onChange={(e) => setYeni({ ...yeni, sifre: e.target.value })}
                  data-testid="new-user-password-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Rol</Label>
                <Select
                  value={yeni.rol}
                  onValueChange={(v: string) => setYeni({ ...yeni, rol: v })}
                >
                  <SelectTrigger data-testid="new-user-role-select">
                    <SelectValue>{(v) => roleLabel(v as string)}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {(roles ?? []).map((r) => (
                      <SelectItem key={r.kod} value={r.kod}>
                        {r.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                type="submit"
                className="w-full"
                disabled={createUser.isPending}
                data-testid="new-user-save-button"
              >
                {createUser.isPending ? "Oluşturuluyor…" : "Kullanıcıyı Oluştur"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Dialog open={!!resetFor} onOpenChange={(o: boolean) => !o && setResetFor(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Şifre Sıfırla — {resetFor?.email}</DialogTitle>
          </DialogHeader>
          <form
            className="space-y-4"
            data-testid="reset-password-form"
            onSubmit={(e) => {
              e.preventDefault();
              resetPassword.mutate();
            }}
          >
            <p className="text-xs text-muted-foreground">
              Yeni şifreyi kullanıcıya iletin. Sıfırlama sonrası bu kullanıcının tüm açık
              oturumları kapatılır.
            </p>
            <div className="space-y-1.5">
              <Label htmlFor="rp-sifre">Yeni Şifre (en az 8 karakter)</Label>
              <Input
                id="rp-sifre"
                required
                minLength={8}
                value={yeniSifre}
                onChange={(e) => setYeniSifre(e.target.value)}
                data-testid="reset-password-input"
              />
            </div>
            <DialogFooter>
              <Button
                type="submit"
                disabled={resetPassword.isPending}
                data-testid="reset-password-save-button"
              >
                {resetPassword.isPending ? "Sıfırlanıyor…" : "Şifreyi Sıfırla"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
