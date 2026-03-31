import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";
import { eventPresentation } from "@/lib/lifecycle";

export function TimelineEvent({ event }: { event: Record<string, unknown> }) {
  const { title, summary, details } = eventPresentation(event);
  const step = event.step !== undefined ? `Step ${String(event.step)}` : "System";
  const createdAt =
    typeof event.created_at === "number" ? formatTimestamp(Number(event.created_at)) : undefined;

  return (
    <div className="rounded-[22px] border border-border bg-surfaceAlt/55 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-white">{title}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.14em] text-muted">
            {step}
            {createdAt ? ` | ${createdAt}` : ""}
          </p>
        </div>
        {event.status ? <StatusBadge status={String(event.status)} /> : null}
      </div>
      <p className="mt-3 text-sm leading-6 text-white/90">{summary}</p>
      <details className="mt-3">
        <summary className="cursor-pointer text-xs uppercase tracking-[0.14em] text-muted">
          Technical details
        </summary>
        <pre className="mt-3 whitespace-pre-wrap text-xs leading-6 text-muted">
          {JSON.stringify(details, null, 2)}
        </pre>
      </details>
    </div>
  );
}
