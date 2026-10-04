import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ShieldCheck, UserPlus, Trash2, Users as UsersIcon, Save, KeyRound, Plus, Pencil } from "lucide-react";
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

const HAZIR_ROLLER = ["admin", "satis", "uretim", "muhasebe", "izleyici"];

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
  const [rolDialog, setRolDialog] = useState(false);
  const [yeniRol, setYeniRol] = useState({ kod: "", label: "" });
  const [adDialog, setAdDialog] = useState(false);
  const [yeniAd, setYeniAd] = useState("");
  const [rolSilOnay, setRolSilOnay] = useState(false);
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

  const createRole = useMutation({
    mutationFn: () =>
      apiPost<Role>("/roles", {
        kod: yeniRol.kod.trim().toLowerCase(),
        label: yeniRol.label.trim(),
        yetkiler: [],
      }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["roles"] });
      setSecili(r.kod);
      setTaslak(null);
      setRolDialog(false);
      setYeniRol({ kod: "", label: "" });
      toast.success(`Rol oluşturuldu: ${r.label} — şimdi yetkileri seçip kaydedin`);
    },
    onError: (e) => toast.error(errText(e, "Rol oluşturulamadı")),
  });

  const renameRole = useMutation({
    mutationFn: () => apiPut<Role>(`/roles/${secili}/ad`, { label: yeniAd.trim() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles"] });
      qc.invalidateQueries({ queryKey: ["my-permissions"] });
      setAdDialog(false);
      toast.success("Rol adı güncellendi");
    },
    onError: (e) => toast.error(errText(e, "Rol adı güncellenemedi")),
  });

  const deleteRole = useMutation({
    mutationFn: () => apiDelete(`/roles/${secili}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles"] });
      setRolSilOnay(false);
      setSecili("satis");
      setTaslak(null);
      toast.success("Rol silindi");
    },
    onError: (e) => toast.error(errText(e, "Rol silinemedi")),
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
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setRolDialog(true)}
                  data-testid="role-create-button"
                >
                  <Plus className="mr-2 h-4 w-4" /> Yeni Rol
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={secili === "admin"}
                  onClick={() => {
                    setYeniAd(rol?.label ?? "");
                    setAdDialog(true);
                  }}
                  title="Rol adını değiştir"
                  data-testid="role-rename-button"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={secili === "admin" || HAZIR_ROLLER.includes(secili)}
                  onClick={() => setRolSilOnay(true)}
                  title="Rolü sil"
                  data-testid="role-delete-button"
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {secili === "admin" && (
                <p className="mb-3 text-xs text-amber-400" data-testid="admin-role-note">
                  Admin rolü daima tüm yetkilere sahiptir ve değiştirilemez.
                </p>
              )}
              {secili !== "admin" && HAZIR_ROLLER.includes(secili) && (
                <p className="mb-3 text-xs text-muted-foreground" data-testid="preset-role-note">
                  Hazır rol — yetkileri ve adı değiştirilebilir, silinemez.
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
      <Dialog open={rolDialog} onOpenChange={setRolDialog}>
        <DialogContent className="sm:max-w-md" data-testid="role-create-dialog">
          <DialogHeader>
            <DialogTitle>Yeni Rol Oluştur</DialogTitle>
          </DialogHeader>
          <form
            className="space-y-4"
            data-testid="role-create-form"
            onSubmit={(e) => {
              e.preventDefault();
              createRole.mutate();
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="nr-label">Rol Adı</Label>
              <Input
                id="nr-label"
                required
                placeholder="Örn. Gümrük Sorumlusu"
                value={yeniRol.label}
                onChange={(e) => setYeniRol({ ...yeniRol, label: e.target.value })}
                data-testid="role-create-label-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="nr-kod">Rol Kodu (harf, rakam, - , _)</Label>
              <Input
                id="nr-kod"
                required
                placeholder="gumruk"
                value={yeniRol.kod}
                onChange={(e) => setYeniRol({ ...yeniRol, kod: e.target.value })}
                data-testid="role-create-code-input"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Rol oluşturulduktan sonra yetkiler listesinden seçim yapıp Kaydet'e basın.
            </p>
            <DialogFooter>
              <Button
                type="submit"
                disabled={createRole.isPending}
                data-testid="role-create-submit-button"
              >
                {createRole.isPending ? "Oluşturuluyor…" : "Rolü Oluştur"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={adDialog} onOpenChange={setAdDialog}>
        <DialogContent className="sm:max-w-md" data-testid="role-rename-dialog">
          <DialogHeader>
            <DialogTitle>Rol Adını Değiştir</DialogTitle>
          </DialogHeader>
          <form
            className="space-y-4"
            data-testid="role-rename-form"
            onSubmit={(e) => {
              e.preventDefault();
              renameRole.mutate();
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="rr-label">Rol Adı</Label>
              <Input
                id="rr-label"
                required
                value={yeniAd}
                onChange={(e) => setYeniAd(e.target.value)}
                data-testid="role-rename-input"
              />
            </div>
            <DialogFooter>
              <Button
                type="submit"
                disabled={renameRole.isPending}
                data-testid="role-rename-submit-button"
              >
                Kaydet
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={rolSilOnay} onOpenChange={setRolSilOnay}>
        <DialogContent className="sm:max-w-md" data-testid="role-delete-dialog">
          <DialogHeader>
            <DialogTitle>Rolü sil?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            {rol?.label} rolü silinecek. Bu role atanmış kullanıcı varsa işlem reddedilir.
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRolSilOnay(false)}
              data-testid="role-delete-cancel-button"
            >
              Vazgeç
            </Button>
            <Button
              variant="destructive"
              disabled={deleteRole.isPending}
              onClick={() => deleteRole.mutate()}
              data-testid="role-delete-confirm-button"
            >
              Rolü Sil
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
