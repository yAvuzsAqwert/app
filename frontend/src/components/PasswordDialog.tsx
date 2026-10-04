import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { KeyRound } from "lucide-react";
import { apiPut, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

function errText(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    const body = err.body as { detail?: unknown } | null;
    if (body && typeof body.detail === "string") return body.detail;
  }
  return fallback;
}

/** Kullanıcının kendi şifresini değiştirmesi (mevcut şifre doğrulanır). */
export default function PasswordDialog() {
  const [open, setOpen] = useState(false);
  const [mevcut, setMevcut] = useState("");
  const [yeni, setYeni] = useState("");
  const [tekrar, setTekrar] = useState("");

  const kaydet = useMutation({
    mutationFn: () => apiPut("/auth/sifre", { mevcut_sifre: mevcut, yeni_sifre: yeni }),
    onSuccess: () => {
      toast.success("Şifreniz değiştirildi — diğer oturumlar kapatıldı");
      setOpen(false);
      setMevcut("");
      setYeni("");
      setTekrar("");
    },
    onError: (e) => toast.error(errText(e, "Şifre değiştirilemedi")),
  });

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start"
        onClick={() => setOpen(true)}
        data-testid="open-password-dialog-button"
      >
        <KeyRound className="mr-2 h-4 w-4" /> Şifremi Değiştir
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Şifremi Değiştir</DialogTitle>
          </DialogHeader>
          <form
            className="space-y-4"
            data-testid="password-change-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (yeni !== tekrar) {
                toast.error("Yeni şifreler birbiriyle uyuşmuyor");
                return;
              }
              kaydet.mutate();
            }}
          >
            <div className="space-y-1.5">
              <Label htmlFor="pw-current">Mevcut Şifre</Label>
              <Input
                id="pw-current"
                type="password"
                required
                value={mevcut}
                onChange={(e) => setMevcut(e.target.value)}
                data-testid="password-current-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pw-new">Yeni Şifre (en az 8 karakter)</Label>
              <Input
                id="pw-new"
                type="password"
                required
                minLength={8}
                value={yeni}
                onChange={(e) => setYeni(e.target.value)}
                data-testid="password-new-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pw-repeat">Yeni Şifre (tekrar)</Label>
              <Input
                id="pw-repeat"
                type="password"
                required
                minLength={8}
                value={tekrar}
                onChange={(e) => setTekrar(e.target.value)}
                data-testid="password-repeat-input"
              />
            </div>
            <DialogFooter>
              <Button
                type="submit"
                disabled={kaydet.isPending}
                data-testid="password-save-button"
              >
                {kaydet.isPending ? "Kaydediliyor…" : "Şifreyi Güncelle"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
