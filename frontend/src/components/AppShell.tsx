import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, FolderKanban, CalendarRange, LogOut, Sun, Search, Building2, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { endSession } from "@/lib/session";
import { useAuth } from "@/lib/useAuth";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/panel", label: "Komuta Paneli", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/projeler", label: "Projeler", icon: FolderKanban, testid: "nav-projects" },
  { to: "/bayiler", label: "Bayi Kartları", icon: Building2, testid: "nav-dealers" },
  { to: "/rapor", label: "Günlük Rapor", icon: CalendarRange, testid: "nav-report" },
  { to: "/tanimlar", label: "Tanımlar", icon: SlidersHorizontal, testid: "nav-settings" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const navigate = useNavigate();

  const logout = async () => {
    await endSession();
    navigate("/giris", { replace: true });
  };

  return (
    <div className="flex min-h-svh bg-background" data-testid="app-shell">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-sidebar lg:flex">
        <div className="flex items-center gap-2.5 border-b border-border px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Sun className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <p className="font-heading text-sm font-bold">PERGOLA TAKİP</p>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Tente & Cam Sistemleri
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {NAV.map(({ to, label, icon: Icon, testid }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={testid}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors duration-150",
                  isActive
                    ? "bg-primary/15 text-primary font-semibold"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-border p-3">
          <div className="mb-2 px-2">
            <p className="truncate text-sm font-medium" data-testid="sidebar-user-name">
              {user?.ad_soyad ?? "—"}
            </p>
            <p className="truncate font-mono text-[11px] text-muted-foreground">
              {user?.email ?? ""}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-muted-foreground hover:text-destructive"
            onClick={logout}
            data-testid="logout-button"
          >
            <LogOut className="mr-2 h-4 w-4" /> Çıkış Yap
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-border bg-sidebar/60 px-5 py-3 lg:hidden">
          <span className="font-heading text-sm font-bold">PERGOLA TAKİP</span>
          <div className="flex gap-1">
            {NAV.map(({ to, icon: Icon, testid }) => (
              <NavLink key={to} to={to} data-testid={`${testid}-mobile`}>
                {({ isActive }) => (
                  <Button variant={isActive ? "secondary" : "ghost"} size="icon-sm">
                    <Icon className="h-4 w-4" />
                  </Button>
                )}
              </NavLink>
            ))}
            <Button variant="ghost" size="icon-sm" onClick={logout} data-testid="logout-button-mobile">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1600px] flex-1 p-5 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div>
        <h1 className="text-2xl font-bold lg:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}

export function EmptyState({ mesaj, icon }: { mesaj: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border py-12 text-center">
      <div className="text-muted-foreground">{icon ?? <Search className="h-6 w-6" />}</div>
      <p className="text-sm text-muted-foreground">{mesaj}</p>
    </div>
  );
}
