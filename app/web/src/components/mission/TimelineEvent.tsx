import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

export function TimelineEvent({ event }: { event: Record<string, unknown> }) {
  const type = String(event.event_type ?? event.action ?? "event");
  const step = event.step !== undefined ? `Step ${String(event.step)}` : "System";
  const createdAt =
    typeof event.created_at === "number" ? formatTimestamp(Number(event.created_at)) : undefined;

  return (
    <div className="rounded-[22px] border border-border bg-surfaceAlt/55 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-white">{type.replaceAll("_", " ")}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.14em] text-muted">
            {step}
            {createdAt ? ` · ${createdAt}` : ""}
          </p>
        </div>
        {event.status ? <StatusBadge status={String(event.status)} /> : null}
      </div>
      <pre className="mt-3 whitespace-pre-wrap text-xs leading-6 text-muted">{JSON.stringify(event, null, 2)}</pre>
    </div>
  );
}
