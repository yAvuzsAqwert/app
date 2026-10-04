import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Sun, ArrowRight } from "lucide-react";
import { apiPost, ApiError } from "@/lib/api";
import { beginSession } from "@/lib/session";
import type { User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useBranding } from "@/lib/useBranding";

const HERO =
  "https://images.unsplash.com/photo-1784288195987-e10511825f4b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzR8MHwxfHNlYXJjaHwyfHxtb2Rlcm4lMjBwZXJnb2xhJTIwYXJjaGl0ZWN0dXJhbHxlbnwwfHx8fDE3OTEwOTAwMjJ8MA&ixlib=rb-4.1.0&q=85";

function errText(err: unknown) {
  if (err instanceof ApiError) {
    const body = err.body as { detail?: unknown } | null;
    if (body && typeof body.detail === "string") return body.detail;
  }
  return "İşlem başarısız oldu";
}

export default function Login() {
  const navigate = useNavigate();
  const { programAdi, logoVar, logoUrl } = useBranding();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("admin@pergola.com");
  const [sifre, setSifre] = useState("pergola123");
  const [adSoyad, setAdSoyad] = useState("");

  const auth = useMutation({
    mutationFn: async () =>
      mode === "login"
        ? apiPost<User>("/auth/login", { email, sifre })
        : apiPost<User>("/auth/register", { email, sifre, ad_soyad: adSoyad }),
    onSuccess: (user) => {
      beginSession();
      toast.success(`Hoş geldiniz, ${user.ad_soyad}`);
      navigate("/panel", { replace: true });
    },
    onError: (err) => toast.error(errText(err)),
  });

  return (
    <div className="grid min-h-svh lg:grid-cols-[1.1fr_1fr]">
      {/* Left hero — renders with or without a backend */}
      <div className="relative hidden overflow-hidden lg:block">
        <img src={HERO} alt="Bioklimatik pergola" className="h-full w-full object-cover" />
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(11,15,23,0.95)_0%,rgba(15,23,42,0.82)_50%,rgba(11,15,23,0.94)_100%)]" />
        <div className="absolute inset-0 flex flex-col justify-between p-12">
          <div className="flex items-center gap-2.5">
            {logoVar ? (
              <img src={logoUrl} alt={programAdi} className="h-7 max-w-[180px] object-contain" />
            ) : (
              <>
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
                  <Sun className="h-5 w-5" />
                </div>
                <span
                  className="font-heading text-sm font-bold tracking-wide"
                  data-testid="login-program-name"
                >
                  {programAdi}
                </span>
              </>
            )}
          </div>
          <div className="max-w-xl">
            <p className="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-primary">
              Pergola · Tente · Sürme & Giyotin Cam
            </p>
            <h2 className="text-4xl font-bold leading-tight">
              Talepten gümrük beyannamesine kadar
              <span className="text-primary"> tek ekrandan takip.</span>
            </h2>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-300">
              Proforma, revizyon, üretim termini, sandık ölçüleri, navlun rezervasyonu, fatura ve
              tahsilat — 11 aşamalı süreç tek akışta, ekibinizle birlikte.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-6 border-t border-white/10 pt-6">
            {[
              ["11", "Süreç Aşaması"],
              ["5", "Taksit Takibi"],
              ["XLSX", "Günlük Rapor"],
            ].map(([v, l]) => (
              <div key={l}>
                <p className="font-mono text-2xl font-semibold text-primary">{v}</p>
                <p className="text-xs uppercase tracking-wide text-slate-400">{l}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right auth panel */}
      <div className="flex items-center justify-center bg-background px-6 py-12">
        <div className="w-full max-w-sm animate-rise-in">
          <div className="mb-8">
            <h1 className="text-2xl font-bold">
              {mode === "login" ? "Panele Giriş" : "Yeni Ekip Hesabı"}
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              {mode === "login"
                ? "E-posta ve şifrenizle oturum açın."
                : "Çalışma arkadaşınız için hesap oluşturun."}
            </p>
          </div>

          <form
            className="space-y-4"
            data-testid="login-form"
            onSubmit={(e) => {
              e.preventDefault();
              auth.mutate();
            }}
          >
            {mode === "register" && (
              <div className="space-y-1.5">
                <Label htmlFor="ad">Ad Soyad</Label>
                <Input
                  id="ad"
                  value={adSoyad}
                  onChange={(e) => setAdSoyad(e.target.value)}
                  placeholder="Ahmet Yılmaz"
                  required
                  data-testid="register-name-input"
                />
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="email">E-posta</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="login-email-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sifre">Şifre</Label>
              <Input
                id="sifre"
                type="password"
                value={sifre}
                onChange={(e) => setSifre(e.target.value)}
                required
                data-testid="login-password-input"
              />
            </div>

            <Button
              type="submit"
              className="w-full transition-transform duration-150 hover:-translate-y-0.5"
              disabled={auth.isPending}
              data-testid="login-submit-button"
            >
              {auth.isPending
                ? "Kontrol ediliyor…"
                : mode === "login"
                  ? "Giriş Yap"
                  : "Hesap Oluştur"}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </form>

          <button
            type="button"
            className="mt-5 text-sm text-muted-foreground underline-offset-4 transition-colors duration-150 hover:text-primary hover:underline"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            data-testid="toggle-auth-mode-button"
          >
            {mode === "login" ? "Yeni hesap oluştur" : "Zaten hesabım var, giriş yap"}
          </button>

          <a
            href="/bayi-giris"
            className="mt-3 block text-sm text-muted-foreground underline-offset-4 transition-colors duration-150 hover:text-primary hover:underline"
            data-testid="to-portal-login-link"
          >
            Bayi misiniz? Bayi portalına giriş →
          </a>

          <div className="mt-8 rounded-md border border-border bg-card p-4">
            <p className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">
              Demo Hesap
            </p>
            <p className="mt-1.5 font-mono text-xs text-foreground">admin@pergola.com</p>
            <p className="font-mono text-xs text-foreground">pergola123</p>
          </div>
        </div>
      </div>
    </div>
  );
}
