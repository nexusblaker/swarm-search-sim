export function EventTimeline({
  events,
}: {
  events: Array<Record<string, unknown>>;
}) {
  return (
    <div className="space-y-3">
      {events.map((event, index) => (
        <div key={index} className="rounded-2xl border border-border bg-surfaceAlt/70 p-4">
          <div className="flex items-center justify-between">
            <p className="font-medium text-white">{String(event.event_type ?? "event")}</p>
            <p className="text-xs uppercase tracking-[0.18em] text-muted">Step {String(event.step ?? "-")}</p>
          </div>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-muted">
            {JSON.stringify(event, null, 2)}
          </pre>
        </div>
      ))}
    </div>
  );
}
