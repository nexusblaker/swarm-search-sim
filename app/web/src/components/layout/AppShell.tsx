import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  BarChart3,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Compass,
  FileText,
  History,
  Home,
  Menu,
  Radar,
  Route,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { cn } from "@/lib/cn";

const navigationGroups = [
  {
    label: "Primary",
    items: [
      { to: "/", label: "Mission Desk", icon: Home, summary: "Start here, open an existing mission, or begin a guided intake." },
      { to: "/mission-intake", label: "New Mission", icon: ClipboardList, summary: "Guided mission intake from situation to recommendation." },
      { to: "/plans", label: "Saved Missions", icon: ClipboardList, summary: "Open and update saved mission plans." },
      { to: "/mission-control", label: "Mission Control", icon: Activity, summary: "Launch, monitor, and intervene." },
      { to: "/replay", label: "Replay", icon: Route, summary: "Inspect mission playback step by step." },
      { to: "/reviews", label: "After Action", icon: ClipboardList, summary: "Summarize lessons and outcomes." },
      { to: "/reports", label: "Reports", icon: FileText, summary: "Open mission briefs, run summaries, and after-action exports." },
    ],
  },
  {
    label: "More Tools",
    items: [
      { to: "/runs", label: "Run History", icon: History, summary: "Browse completed and active mission runs." },
      { to: "/comparisons", label: "Mission Options", icon: Radar, summary: "Compare alternative mission options before launch." },
      { to: "/recommendations", label: "Plan Briefs", icon: ShieldCheck, summary: "Review recommendation briefings and rationale." },
      { to: "/library", label: "Sample Missions", icon: BookOpen, summary: "Browse starting points and training examples." },
      { to: "/scenarios", label: "Scenarios", icon: Compass, summary: "Define search conditions and assumptions." },
      { to: "/experiments", label: "Experiments", icon: BarChart3, summary: "Review grouped robustness analysis." },
    ],
  },
];

const pageMeta = Object.fromEntries(
  navigationGroups.flatMap((group) => group.items.map((item) => [item.to, item])),
);

export function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const current = pageMeta[location.pathname] ?? pageMeta["/"];
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    const applySidebarPreference = () => {
      const stored = window.localStorage.getItem("swarm-sidebar-collapsed");
      const isNarrowDesktop = window.innerWidth < 1480;
      setSidebarCollapsed(isNarrowDesktop ? true : stored === "true");
    };

    applySidebarPreference();
    window.addEventListener("resize", applySidebarPreference);
    return () => window.removeEventListener("resize", applySidebarPreference);
  }, []);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  const primaryLinks = useMemo(() => navigationGroups[0].items, []);
  const secondaryLinks = useMemo(() => navigationGroups[1].items, []);
  const handleSidebarToggle = () => {
    setSidebarCollapsed((value) => {
      const next = !value;
      window.localStorage.setItem("swarm-sidebar-collapsed", String(next));
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-ops-grid bg-background bg-ops-grid text-text">
      <div className="mx-auto flex min-h-screen max-w-[1680px] gap-6 px-4 py-4 lg:px-6">
        <motion.aside
          layout
          transition={{ type: "spring", stiffness: 260, damping: 28 }}
          className={cn(
            "sticky top-4 hidden h-[calc(100vh-2rem)] shrink-0 overflow-hidden rounded-[32px] border border-border/80 bg-surface/92 shadow-panel backdrop-blur xl:flex xl:flex-col",
            sidebarCollapsed ? "w-[94px]" : "w-[296px]",
          )}
        >
          <div className={cn("flex items-start justify-between border-b border-border/70 px-4 pb-5 pt-5", sidebarCollapsed && "px-3")}>
            <div className={cn("min-w-0", sidebarCollapsed && "sr-only")}>
              <p className="text-[11px] uppercase tracking-[0.32em] text-muted">Swarm Console</p>
              <h1 className="mt-2 text-[24px] font-semibold text-white">Mission Desk</h1>
              <p className="mt-3 text-sm leading-6 text-muted">
                A calmer operator workspace for planning, simulation, monitoring, replay, and review.
              </p>
            </div>
            <button
              type="button"
              onClick={handleSidebarToggle}
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              className="ml-auto inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-border/80 bg-surfaceAlt/80 text-muted transition duration-150 hover:bg-white/[0.06] hover:text-white"
            >
              {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>
          <div className="scrollbar-subtle flex-1 space-y-7 overflow-y-auto px-3 py-5">
            {navigationGroups.map((group) => (
              <div key={group.label}>
                {!sidebarCollapsed && <p className="mb-2 px-2 text-[11px] uppercase tracking-[0.2em] text-muted">{group.label}</p>}
                <div className="space-y-1.5">
                  {group.items.map(({ to, label, icon: Icon }) => (
                    <NavLink
                      key={to}
                      to={to}
                      title={label}
                      className={({ isActive }) =>
                        cn(
                          "group flex items-center rounded-[20px] border text-sm transition duration-150",
                          sidebarCollapsed ? "justify-center px-3 py-3.5" : "gap-3 px-4 py-3.5",
                          isActive
                            ? "border-border bg-white/[0.06] text-white shadow-soft"
                            : "border-transparent text-muted hover:border-border/80 hover:bg-surfaceAlt/55 hover:text-white",
                        )
                      }
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {!sidebarCollapsed && <span className="truncate">{label}</span>}
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {!sidebarCollapsed && (
            <div className="border-t border-border/70 px-4 py-4">
              <div className="rounded-[24px] border border-border/70 bg-surfaceAlt/55 p-4">
                <p className="section-kicker">Current view</p>
                <p className="mt-2 text-base font-semibold text-white">{current.label}</p>
                <p className="mt-2 text-sm leading-6 text-muted">{current.summary}</p>
              </div>
            </div>
          )}
        </motion.aside>
        <div className="flex min-h-screen flex-1 flex-col">
          <header className="sticky top-4 z-20 mb-5 rounded-[30px] border border-border/80 bg-surface/85 px-5 py-5 shadow-panel backdrop-blur md:px-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.24em] text-muted">Operator Interface</p>
                <h2 className="mt-2 text-[30px] font-semibold text-white">{current.label}</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{current.summary}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="pill">Mission planning</span>
                <span className="pill">Live operations</span>
                <span className="pill">Replay and review</span>
                <button
                  type="button"
                  onClick={() => setMobileNavOpen((value) => !value)}
                  className="nav-chip xl:hidden"
                  aria-expanded={mobileNavOpen}
                >
                  <Menu className="h-4 w-4" />
                  Navigate
                </button>
              </div>
            </div>
            <AnimatePresence initial={false}>
              {mobileNavOpen && (
                <motion.div
                  key="mobile-nav"
                  initial={{ opacity: 0, y: -8, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: "auto" }}
                  exit={{ opacity: 0, y: -8, height: 0 }}
                  transition={{ duration: 0.18, ease: "easeOut" }}
                  className="overflow-hidden xl:hidden"
                >
                  <div className="mt-5 grid gap-3 border-t border-border/70 pt-5 md:grid-cols-2">
                    <div className="space-y-2">
                      <p className="micro-label">Primary</p>
                      <div className="flex flex-wrap gap-2">
                        {primaryLinks.map(({ to, label, icon: Icon }) => (
                          <NavLink
                            key={to}
                            to={to}
                            className={({ isActive }) =>
                              cn("nav-chip", isActive && "border-accentStrong/35 bg-white/[0.08] text-white")
                            }
                          >
                            <Icon className="h-4 w-4" />
                            {label}
                          </NavLink>
                        ))}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <p className="micro-label">More tools</p>
                      <div className="flex flex-wrap gap-2">
                        {secondaryLinks.map(({ to, label, icon: Icon }) => (
                          <NavLink
                            key={to}
                            to={to}
                            className={({ isActive }) =>
                              cn("nav-chip", isActive && "border-accentStrong/35 bg-white/[0.08] text-white")
                            }
                          >
                            <Icon className="h-4 w-4" />
                            {label}
                          </NavLink>
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </header>
          <motion.main
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="flex-1"
          >
            {children}
          </motion.main>
        </div>
      </div>
    </div>
  );
}
