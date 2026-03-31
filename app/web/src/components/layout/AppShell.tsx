import { Activity, BarChart3, BookOpen, ClipboardList, Compass, FileText, History, Home, Radar, Route, ShieldCheck } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";

import { cn } from "@/lib/cn";

const navigationGroups = [
  {
    label: "Planning",
    items: [
      { to: "/", label: "Mission Desk", icon: Home, summary: "Start here, open an existing mission, or begin a guided intake." },
      { to: "/mission-intake", label: "New Mission", icon: ClipboardList, summary: "Guided mission intake from situation to recommendation." },
      { to: "/scenarios", label: "Scenarios", icon: Compass, summary: "Define search conditions and assumptions." },
      { to: "/plans", label: "Saved Missions", icon: ClipboardList, summary: "Open and update saved mission plans." },
      { to: "/library", label: "Sample Missions", icon: BookOpen, summary: "Browse polished starting points and presets." },
      { to: "/comparisons", label: "Mission Options", icon: Radar, summary: "Rank alternative plan options before launch." },
      { to: "/recommendations", label: "Plan Brief", icon: ShieldCheck, summary: "Review explainable recommendation briefs." },
    ],
  },
  {
    label: "Execution",
    items: [
      { to: "/mission-control", label: "Mission Control", icon: Activity, summary: "Launch, monitor, and intervene." },
      { to: "/replay", label: "Replay", icon: Route, summary: "Inspect mission playback step by step." },
      { to: "/runs", label: "Run History", icon: History, summary: "Browse completed and active mission runs." },
    ],
  },
  {
    label: "Review",
    items: [
      { to: "/experiments", label: "Experiments", icon: BarChart3, summary: "Review grouped robustness analysis." },
      { to: "/reports", label: "Reports", icon: FileText, summary: "Open indexed exports and artifacts." },
      { to: "/reviews", label: "After Action", icon: ClipboardList, summary: "Summarize lessons and outcomes." },
    ],
  },
];

const pageMeta = Object.fromEntries(
  navigationGroups.flatMap((group) => group.items.map((item) => [item.to, item])),
);

export function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const current = pageMeta[location.pathname] ?? pageMeta["/"];

  return (
    <div className="min-h-screen bg-ops-grid bg-background bg-ops-grid text-text">
      <div className="mx-auto flex min-h-screen max-w-[1680px] gap-6 px-4 py-4 lg:px-6">
        <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] w-[296px] shrink-0 rounded-[32px] border border-border/80 bg-surface/92 p-5 shadow-panel backdrop-blur xl:block">
          <div className="mb-8 border-b border-border/70 pb-6">
            <p className="text-[11px] uppercase tracking-[0.32em] text-muted">Swarm Console</p>
            <h1 className="mt-2 text-[24px] font-semibold text-white">Mission Desk</h1>
            <p className="mt-3 text-sm leading-6 text-muted">
              A calmer operator workspace for planning, simulation, monitoring, replay, and review.
            </p>
          </div>
          <nav className="space-y-6">
            {navigationGroups.map((group) => (
              <div key={group.label}>
                <p className="mb-2 px-2 text-[11px] uppercase tracking-[0.2em] text-muted">{group.label}</p>
                <div className="space-y-1.5">
                  {group.items.map(({ to, label, icon: Icon }) => (
                    <NavLink
                      key={to}
                      to={to}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 rounded-[20px] border px-4 py-3 text-sm transition",
                          isActive
                            ? "border-border bg-white/[0.06] text-white shadow-soft"
                            : "border-transparent text-muted hover:border-border/80 hover:bg-surfaceAlt/55 hover:text-white",
                        )
                      }
                    >
                      <Icon className="h-4 w-4" />
                      <span>{label}</span>
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
          </nav>
          <div className="mt-8 rounded-[24px] border border-border/70 bg-surfaceAlt/55 p-4">
            <p className="section-kicker">Workflow</p>
            <p className="mt-2 text-sm leading-6 text-muted">
              Start a mission, review the plan, launch a run, then monitor, replay, review, and report.
            </p>
          </div>
        </aside>
        <div className="flex min-h-screen flex-1 flex-col">
          <header className="sticky top-4 z-20 mb-5 rounded-[30px] border border-border/80 bg-surface/85 px-6 py-5 shadow-panel backdrop-blur">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted">Operator Interface</p>
                <h2 className="mt-1 text-[28px] font-semibold text-white">{current.label}</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{current.summary}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="pill">React primary UI</span>
                <span className="pill">FastAPI backend</span>
                <span className="pill">Simulation core preserved</span>
              </div>
            </div>
            <div className="scrollbar-subtle mt-5 flex gap-2 overflow-x-auto xl:hidden">
              {navigationGroups.flatMap((group) => group.items).map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    cn("pill whitespace-nowrap", isActive && "border-accentStrong/40 text-white")
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>
          </header>
          <main className="flex-1">{children}</main>
        </div>
      </div>
    </div>
  );
}
