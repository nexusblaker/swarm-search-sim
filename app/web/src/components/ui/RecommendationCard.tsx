import type { AssetPackage, ConfidenceSummary, FeasibilitySummary } from "@/api/types";
import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel";
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
  searchPattern,
  searchPatternLabel,
  searchPatternSummary,
  searchPatternReason,
  searchPatternFitSummary,
  drones,
  reserveThreshold,
  explanation,
  conciseSummary,
  topAlternativeSummary,
  keyTradeoffs = [],
  keyRisks = [],
  teamCoordinationLabel,
  assetPackage,
  confidenceSummary,
  feasibilitySummary,
  riskSummary,
  uncertaintySummary,
  technicalDetails,
}: {
  strategy?: string | null;
  searchPattern?: string | null;
  searchPatternLabel?: string | null;
  searchPatternSummary?: string | null;
  searchPatternReason?: string | null;
  searchPatternFitSummary?: string | null;
  drones?: number | null;
  reserveThreshold?: number | null;
  explanation: string;
  conciseSummary?: string;
  topAlternativeSummary?: string | null;
  keyTradeoffs?: string[];
  keyRisks?: string[];
  teamCoordinationLabel?: string | null;
  assetPackage?: AssetPackage | null;
  confidenceSummary?: ConfidenceSummary;
  feasibilitySummary?: FeasibilitySummary;
  riskSummary?: Record<string, unknown>;
  uncertaintySummary?: Record<string, unknown>;
  technicalDetails?: Record<string, unknown>;
}) {
  const primarySummary = conciseSummary ?? explanation;
  const mainRisk = (keyRisks.length ? keyRisks : ["No major operational risk was flagged in the short evaluation bundle."])[0];
  const mainTradeoff = (keyTradeoffs.length
    ? keyTradeoffs
    : ["Balances speed, confidence, and reserve without a major compromise."])[0];
  const patternTitle = searchPatternLabel ?? searchPattern ?? strategy ?? "Recommended pattern";
  const missionAreaSummary =
    typeof technicalDetails?.mission_area_summary === "string"
      ? technicalDetails.mission_area_summary
      : typeof technicalDetails?.mission_area === "object" &&
          technicalDetails.mission_area !== null &&
          typeof (technicalDetails.mission_area as Record<string, unknown>).operator_summary === "string"
        ? ((technicalDetails.mission_area as Record<string, unknown>).operator_summary as string)
        : null;
  const feasibilityWarnings = feasibilitySummary?.warnings ?? [];
  const firstCandidateBand =
    typeof technicalDetails?.first_candidate_band === "object" && technicalDetails.first_candidate_band !== null
      ? (technicalDetails.first_candidate_band as Record<string, number>)
      : null;
  const confirmedBand =
    typeof technicalDetails?.confirmed_detection_band === "object" && technicalDetails.confirmed_detection_band !== null
      ? (technicalDetails.confirmed_detection_band as Record<string, number>)
      : null;
  const confidenceLabel =
    confidenceSummary?.confidence_level === "high"
      ? "High confidence"
      : confidenceSummary?.confidence_level === "moderate"
        ? "Moderate confidence"
        : confidenceSummary?.confidence_level === "low"
          ? "Low confidence"
          : "Confidence pending";
  const feasibilityLabel = feasibilitySummary?.status_label ?? "Mission readiness";
  const feasibilityTone: "good" | "warning" | "danger" =
    feasibilitySummary?.status === "likely_infeasible"
      ? "danger"
      : feasibilitySummary?.status === "high_risk"
        ? "warning"
        : feasibilitySummary?.status === "warning"
          ? "warning"
          : "good";

  return (
    <div className="panel-subtle p-5 md:p-6">
      <p className="section-kicker">Recommended plan</p>
      <h3 className="mt-3 max-w-4xl text-[28px] font-semibold leading-tight text-white">{primarySummary}</h3>
      <p className="mt-3 max-w-3xl text-base leading-7 text-muted">{explanation}</p>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-[24px] border border-border bg-white/[0.04] p-5">
          <p className="section-kicker">Recommended pattern</p>
          <p className="mt-3 text-xl font-semibold text-white">{patternTitle}</p>
          <p className="mt-3 text-sm leading-7 text-muted">
            {searchPatternSummary ?? "Pattern summary not available."}
          </p>
          <p className="mt-3 text-sm leading-7 text-muted">
            {searchPatternReason ?? mainTradeoff}
          </p>
          {searchPatternFitSummary ? (
            <p className="mt-3 text-sm leading-7 text-white/90">{searchPatternFitSummary}</p>
          ) : null}
          {missionAreaSummary ? (
            <p className="mt-3 text-sm leading-7 text-white/90">{missionAreaSummary}</p>
          ) : null}
          {assetPackage?.operator_summary ? (
            <p className="mt-3 text-sm leading-7 text-muted">{assetPackage.operator_summary}</p>
          ) : null}
          {teamCoordinationLabel ? (
            <p className="mt-3 text-sm leading-7 text-muted">Team coordination style: {teamCoordinationLabel}.</p>
          ) : null}
          <div className="mt-5 rounded-[20px] border border-border/70 bg-surfaceAlt/55 p-4">
            <p className="micro-label">Next action</p>
            <p className="mt-2 text-sm leading-6 text-white">
              Continue to save the mission plan, compare it against alternatives, or launch a simulation.
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[24px] border border-danger/20 bg-danger/10 p-5">
            <p className="section-kicker">Main risk</p>
            <p className="mt-3 text-sm leading-7 text-white/92">{mainRisk}</p>
          </div>

          <div className="rounded-[24px] border border-border bg-surfaceAlt/50 p-5">
            <p className="section-kicker">{feasibilityLabel}</p>
            <p className="mt-3 text-sm leading-7 text-muted">
              {feasibilitySummary?.operator_summary ?? "No mission-feasibility watch item was returned."}
            </p>
            {feasibilitySummary?.next_watch ? (
              <p className="mt-3 text-sm leading-7 text-white/90">Watch next: {feasibilitySummary.next_watch}</p>
            ) : null}
          </div>

          <div className="rounded-[24px] border border-border bg-surfaceAlt/50 p-5">
            <p className="section-kicker">Best alternative</p>
            <p className="mt-3 text-sm leading-7 text-muted">
              {topAlternativeSummary ?? "No close alternative was returned in this evaluation bundle."}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-5">
        <RiskIndicator label="Search pattern" value={patternTitle} tone="good" />
        <RiskIndicator label="Drone count" value={drones ? String(drones) : "n/a"} />
        <RiskIndicator
          label="Reserve threshold"
          value={reserveThreshold !== null && reserveThreshold !== undefined ? `${reserveThreshold}%` : "n/a"}
        />
        <RiskIndicator label="Confidence" value={confidenceLabel} tone="good" />
        <RiskIndicator label="Mission readiness" value={feasibilityLabel} tone={feasibilityTone} />
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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
          <p className="section-kicker">Expected timing</p>
          <div className="mt-3 space-y-2">
            <p className="text-sm leading-6 text-muted">
              {firstCandidateBand
                ? `First candidate: ${Math.round(Number(firstCandidateBand.low ?? 0))} to ${Math.round(Number(firstCandidateBand.high ?? 0))} minutes`
                : "First candidate window not available."}
            </p>
            <p className="text-sm leading-6 text-muted">
              {confirmedBand
                ? `Confirmed contact: ${Math.round(Number(confirmedBand.low ?? 0))} to ${Math.round(Number(confirmedBand.high ?? 0))} minutes`
                : "Confirmed-contact window not available."}
            </p>
          </div>
        </div>

        <div className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
          <p className="section-kicker">Confidence range</p>
          <div className="mt-3 space-y-2">
            <p className="text-sm leading-6 text-white/90">{confidenceLabel}</p>
            <p className="text-sm leading-6 text-muted">
              {confidenceSummary?.confidence_reason ?? "Confidence notes were not returned for this recommendation."}
            </p>
          </div>
        </div>

        <div className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
            <p className="section-kicker">Planning watch items</p>
            <div className="mt-3 space-y-2">
              {(feasibilityWarnings.length
                ? feasibilityWarnings.map((item) => item.summary ?? item.title ?? "")
                : keyRisks.length
                  ? keyRisks
                  : ["No major operational risk was flagged in the short evaluation bundle."]).map((item, index) => (
                <p key={`${item}-${index}`} className="text-sm leading-6 text-muted">
                  {item}
                </p>
              ))}
            </div>
          </div>
      </div>

      <div className="mt-5">
        <CollapsiblePanel
          title="Technical details"
          description="Open the structured inputs and risk notes behind this recommendation."
          defaultOpen={false}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <DetailRows title="Risk summary" record={riskSummary} />
            <DetailRows title="Uncertainty" record={uncertaintySummary} />
            <DetailRows title="Recommendation details" record={technicalDetails} />
            <DetailRows title="Confidence summary" record={confidenceSummary as unknown as Record<string, unknown>} />
            <DetailRows title="Feasibility summary" record={feasibilitySummary as unknown as Record<string, unknown>} />
            {assetPackage?.fleet_composition ? (
              <DetailRows
                title="Fleet composition"
                record={assetPackage.fleet_composition as unknown as Record<string, unknown>}
              />
            ) : null}
          </div>
        </CollapsiblePanel>
      </div>
    </div>
  );
}
