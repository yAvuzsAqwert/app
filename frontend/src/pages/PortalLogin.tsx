import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Sun, ArrowRight, ShieldCheck } from "lucide-react";
import { apiPost, ApiError } from "@/lib/api";
import type { DealerAccount } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function errText(err: unknown) {
  if (err instanceof ApiError) {
    const body = err.body as { detail?: unknown } | null;
    if (body && typeof body.detail === "string") return body.detail;
  }
  return "Giriş yapılamadı";
}

export default function PortalLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [sifre, setSifre] = useState("");

  const login = useMutation({
    mutationFn: () => apiPost<DealerAccount>("/portal/login", { email, sifre }),
    onSuccess: (acc) => {
      toast.success(`Hoş geldiniz, ${acc.firma}`);
      navigate("/bayi", { replace: true });
    },
    onError: (err) => toast.error(errText(err)),
  });

  return (
    <div className="flex min-h-svh items-center justify-center bg-background px-6 py-12">
      <div className="w-full max-w-sm animate-rise-in" data-testid="portal-login-page">
        <div className="mb-8 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Sun className="h-5 w-5" />
          </div>
          <span className="font-heading text-sm font-bold tracking-wide">BAYİ PORTALI</span>
        </div>

        <h1 className="text-2xl font-bold">Bayi Girişi</h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Kendi projelerinizi, tahsilatlarınızı ve açık bakiyenizi görüntüleyin.
        </p>

        <form
          className="mt-7 space-y-4"
          data-testid="portal-login-form"
          onSubmit={(e) => {
            e.preventDefault();
            login.mutate();
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="p-email">E-posta</Label>
            <Input
              id="p-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              data-testid="portal-email-input"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-sifre">Şifre</Label>
            <Input
              id="p-sifre"
              type="password"
              required
              value={sifre}
              onChange={(e) => setSifre(e.target.value)}
              data-testid="portal-password-input"
            />
          </div>
          <Button
            type="submit"
            className="w-full transition-transform duration-150 hover:-translate-y-0.5"
            disabled={login.isPending}
            data-testid="portal-login-submit"
          >
            {login.isPending ? "Kontrol ediliyor…" : "Giriş Yap"}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </form>

        <p className="mt-6 flex items-start gap-2 text-xs text-muted-foreground">
          <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
          Portal salt okunurdur — bilgileri yalnızca görüntüleyebilirsiniz. Erişim için
          temsilcinizden hesap talep edin.
        </p>
        <Link
          to="/giris"
          className="mt-4 inline-block text-sm text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
          data-testid="portal-to-team-login"
        >
          Ekip girişine dön
        </Link>
      </div>
    </div>
  );
}
