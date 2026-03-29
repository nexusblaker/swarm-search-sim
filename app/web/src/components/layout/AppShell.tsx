import { Activity, BarChart3, BookOpen, ClipboardList, Compass, FileText, History, Home, Radar, Route, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/cn";

const navigation = [
  { to: "/", label: "Dashboard", icon: Home },
  { to: "/scenarios", label: "Scenarios", icon: Compass },
  { to: "/plans", label: "Mission Plans", icon: ClipboardList },
  { to: "/library", label: "Doctrine Library", icon: BookOpen },
  { to: "/comparisons", label: "Plan Comparison", icon: Radar },
  { to: "/recommendations", label: "Recommendations", icon: ShieldCheck },
  { to: "/mission-control", label: "Mission Control", icon: Activity },
  { to: "/replay", label: "Replay", icon: Route },
  { to: "/runs", label: "Run History", icon: History },
  { to: "/experiments", label: "Experiments", icon: BarChart3 },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/reviews", label: "After Action", icon: ClipboardList },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-ops-grid bg-background bg-ops-grid text-text">
      <div className="mx-auto flex min-h-screen max-w-[1680px] gap-6 px-4 py-4 lg:px-6">
        <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-72 shrink-0 rounded-3xl border border-border bg-surface/90 p-5 shadow-panel backdrop-blur xl:block">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.3em] text-accent">Swarm</p>
            <h1 className="mt-2 text-xl font-semibold text-white">Mission Console</h1>
            <p className="mt-2 text-sm text-muted">
              Planning, simulation, monitoring, replay, and review for search-and-rescue missions.
            </p>
          </div>
          <nav className="space-y-2">
            {navigation.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition",
                    isActive
                      ? "border-accent/40 bg-accent/10 text-white"
                      : "border-transparent bg-surfaceAlt/70 text-muted hover:border-border hover:text-white",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </aside>
        <div className="flex min-h-screen flex-1 flex-col">
          <header className="mb-5 rounded-3xl border border-border bg-surface/80 px-6 py-5 shadow-panel backdrop-blur">
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-accent">Operator Interface</p>
                <h2 className="mt-1 text-2xl font-semibold text-white">Mission Planning And Evaluation</h2>
              </div>
              <p className="max-w-2xl text-sm text-muted">
                React is now the primary product UI. The backend remains FastAPI-based and the simulation engine remains under
                the existing core.
              </p>
            </div>
          </header>
          <main className="flex-1">{children}</main>
        </div>
      </div>
    </div>
  );
}
