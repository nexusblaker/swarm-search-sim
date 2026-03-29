import { RiskIndicator } from "@/components/ui/RiskIndicator";

export function RecommendationCard({
  strategy,
  drones,
  reserveThreshold,
  explanation,
  riskSummary,
  uncertaintySummary,
}: {
  strategy?: string | null;
  drones?: number | null;
  reserveThreshold?: number | null;
  explanation: string;
  riskSummary?: Record<string, unknown>;
  uncertaintySummary?: Record<string, unknown>;
}) {
  return (
    <div className="panel-subtle p-5">
      <p className="section-kicker">Recommended setup</p>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <RiskIndicator label="Strategy" value={strategy ?? "n/a"} tone="good" />
        <RiskIndicator label="Drone count" value={drones ? String(drones) : "n/a"} />
        <RiskIndicator
          label="Reserve threshold"
          value={reserveThreshold !== null && reserveThreshold !== undefined ? `${reserveThreshold}%` : "n/a"}
        />
      </div>
      <p className="mt-5 text-sm leading-7 text-muted">{explanation}</p>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-[22px] border border-border bg-surfaceAlt/60 p-4">
          <p className="section-kicker">Risk summary</p>
          <pre className="mt-3 whitespace-pre-wrap text-xs leading-6 text-muted">
            {JSON.stringify(riskSummary ?? {}, null, 2)}
          </pre>
        </div>
        <div className="rounded-[22px] border border-border bg-surfaceAlt/60 p-4">
          <p className="section-kicker">Uncertainty</p>
          <pre className="mt-3 whitespace-pre-wrap text-xs leading-6 text-muted">
            {JSON.stringify(uncertaintySummary ?? {}, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
