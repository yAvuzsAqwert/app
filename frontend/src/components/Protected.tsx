import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/useAuth";
import AppShell from "@/components/AppShell";

export default function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading, unauthenticated } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          Yükleniyor…
        </p>
      </div>
    );
  }
  if (unauthenticated || !user) return <Navigate to="/giris" replace />;
  return <AppShell>{children}</AppShell>;
}
