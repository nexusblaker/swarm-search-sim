import type { ResourceStatus } from "@/api/types";
import { cn } from "@/lib/cn";

const statusStyles: Record<string, string> = {
  queued: "bg-slate-500/20 text-slate-300 border-slate-400/30",
  running: "bg-sky-500/20 text-sky-300 border-sky-400/30",
  paused: "bg-amber-500/20 text-amber-300 border-amber-400/30",
  completed: "bg-emerald-500/20 text-emerald-300 border-emerald-400/30",
  failed: "bg-rose-500/20 text-rose-300 border-rose-400/30",
  cancelled: "bg-zinc-500/20 text-zinc-300 border-zinc-400/30",
  draft: "bg-zinc-500/20 text-zinc-300 border-zinc-400/30",
  recommended: "bg-sky-500/20 text-sky-300 border-sky-400/30",
  approved: "bg-emerald-500/20 text-emerald-300 border-emerald-400/30",
  archived: "bg-slate-600/20 text-slate-300 border-slate-400/30",
};

export function StatusBadge({ status }: { status?: string | ResourceStatus | null }) {
  const normalized = (status ?? "unknown").toString().toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium uppercase tracking-[0.18em]",
        statusStyles[normalized] ?? "border-border bg-surfaceAlt text-muted",
      )}
    >
      {normalized}
    </span>
  );
}
