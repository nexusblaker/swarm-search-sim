import type { AssetPackage } from "@/api/types";
import { RiskIndicator } from "@/components/ui/RiskIndicator";

function formatDetailValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "n/a";
  if (Array.isArray(value)) return value.map((item) => formatDetailValue(item)).join(", ");
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.mean === "number" && typeof record.low === "number" && typeof record.high === "number") {
      return `${record.mean.toFixed(2)} mean (${record.low.toFixed(2)}-${record.high.toFixed(2)})`;
    }
    return Object.entries(record)
      .slice(0, 4)
      .map(([key, entry]) => `${key.replaceAll("_", " ")}: ${formatDetailValue(entry)}`)
      .join(" | ");
  }
  return String(value);
}

function DetailRows({ title, record }: { title: string; record?: Record<string, unknown> }) {
  const entries = Object.entries(record ?? {}).filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (entries.length === 0) return null;

  return (
    <div className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
      <p className="section-kicker">{title}</p>
      <div className="mt-3 space-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-start justify-between gap-4">
            <p className="text-sm text-muted">{key.replaceAll("_", " ")}</p>
            <p className="max-w-[60%] text-right text-sm font-medium text-white">{formatDetailValue(value)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function RecommendationCard({
  strategy,
  drones,
  reserveThreshold,
  explanation,
  conciseSummary,
  topAlternativeSummary,
  keyTradeoffs = [],
  keyRisks = [],
  teamCoordinationLabel,
  assetPackage,
  riskSummary,
  uncertaintySummary,
  technicalDetails,
}: {
  strategy?: string | null;
  drones?: number | null;
  reserveThreshold?: number | null;
  explanation: string;
  conciseSummary?: string;
  topAlternativeSummary?: string | null;
  keyTradeoffs?: string[];
  keyRisks?: string[];
  teamCoordinationLabel?: string | null;
  assetPackage?: AssetPackage | null;
  riskSummary?: Record<string, unknown>;
  uncertaintySummary?: Record<string, unknown>;
  technicalDetails?: Record<string, unknown>;
}) {
  return (
    <div className="panel-subtle p-5">
      <p className="section-kicker">Recommended plan</p>
      <h3 className="mt-3 text-2xl font-semibold text-white">{conciseSummary ?? explanation}</h3>

      <div className="mt-5 grid gap-4 md:grid-cols-3">
        <RiskIndicator label="Search style" value={strategy ?? "n/a"} tone="good" />
        <RiskIndicator label="Drone count" value={drones ? String(drones) : "n/a"} />
        <RiskIndicator
          label="Reserve threshold"
          value={reserveThreshold !== null && reserveThreshold !== undefined ? `${reserveThreshold}%` : "n/a"}
        />
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
          <p className="section-kicker">Why this fits</p>
          <p className="mt-3 text-sm leading-7 text-muted">{explanation}</p>
          {assetPackage?.operator_summary ? (
            <p className="mt-3 text-sm leading-7 text-muted">{assetPackage.operator_summary}</p>
          ) : null}
          {teamCoordinationLabel ? (
            <p className="mt-3 text-sm leading-7 text-muted">Team coordination: {teamCoordinationLabel}.</p>
          ) : null}
        </div>

        <div className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
          <p className="section-kicker">Top alternative</p>
          <p className="mt-3 text-sm leading-7 text-muted">
            {topAlternativeSummary ?? "No close alternative was returned in this evaluation bundle."}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
          <p className="section-kicker">Key tradeoffs</p>
          <div className="mt-3 space-y-2">
            {(keyTradeoffs.length ? keyTradeoffs : ["Balances speed, confidence, and reserve without a major compromise."]).map((item) => (
              <p key={item} className="text-sm leading-6 text-muted">
                {item}
              </p>
            ))}
          </div>
        </div>

        <div className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
          <p className="section-kicker">Key risks</p>
          <div className="mt-3 space-y-2">
            {(keyRisks.length ? keyRisks : ["No major operational risk was flagged in the short evaluation bundle."]).map((item) => (
              <p key={item} className="text-sm leading-6 text-muted">
                {item}
              </p>
            ))}
          </div>
        </div>
      </div>

      <details className="mt-5 rounded-[22px] border border-border bg-surfaceAlt/35 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-white">Technical details</summary>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <DetailRows title="Risk summary" record={riskSummary} />
          <DetailRows title="Uncertainty" record={uncertaintySummary} />
          <DetailRows title="Recommendation details" record={technicalDetails} />
          {assetPackage?.fleet_composition ? (
            <DetailRows
              title="Fleet composition"
              record={assetPackage.fleet_composition as unknown as Record<string, unknown>}
            />
          ) : null}
        </div>
      </details>
    </div>
  );
}

