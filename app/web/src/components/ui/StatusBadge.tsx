import type { ResourceStatus } from "@/api/types";
import { cn } from "@/lib/cn";

const statusStyles: Record<string, string> = {
  queued: "border-zinc-500/35 bg-zinc-500/12 text-zinc-200",
  running: "border-[#6f8aa4]/40 bg-[#6f8aa4]/16 text-[#d2e0ec]",
  paused: "border-warning/40 bg-warning/15 text-[#e6d7bc]",
  completed: "border-success/40 bg-success/15 text-[#dce7e0]",
  failed: "border-danger/40 bg-danger/15 text-[#ecd6d9]",
  cancelled: "border-zinc-500/35 bg-zinc-500/12 text-zinc-300",
  draft: "border-zinc-500/35 bg-zinc-500/12 text-zinc-300",
  recommended: "border-[#6f8aa4]/40 bg-[#6f8aa4]/16 text-[#d2e0ec]",
  approved: "border-success/40 bg-success/15 text-[#dce7e0]",
  archived: "border-zinc-500/35 bg-zinc-500/12 text-zinc-300",
};

export function StatusBadge({ status }: { status?: string | ResourceStatus | null }) {
  const normalized = (status ?? "unknown").toString().toLowerCase();
  const label = normalized.replace(/_/g, " ");
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.16em]",
        statusStyles[normalized] ?? "border-border bg-surfaceAlt text-muted",
      )}
    >
      {label}
    </span>
  );
}
