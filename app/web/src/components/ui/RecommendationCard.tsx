import type { AssetPackage, ConfidenceSummary, FeasibilitySummary } from "@/api/types";
import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel";

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

function normalizeCopy(value: string): string {
  return value
    .toLowerCase()
    .replace(/^recommended:\s*/i, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function uniqueCopy(values: Array<string | null | undefined>, limit?: number): string[] {
  const seen = new Set<string>();
  const items: string[] = [];
  for (const value of values) {
    if (!value) continue;
    const trimmed = value.trim();
    if (!trimmed) continue;
    const normalized = normalizeCopy(trimmed);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    items.push(trimmed);
    if (limit && items.length >= limit) break;
  }
  return items;
}

function stripRecommendedPrefix(value: string): string {
  return value.replace(/^recommended:\s*/i, "").trim();
}

function formatMinuteWindow(
  band: Record<string, number> | null,
  prefix: string,
  missingMessage: string,
): string {
  if (!band) return missingMessage;
  const low = typeof band.low === "number" ? Math.round(band.low) : null;
  const high = typeof band.high === "number" ? Math.round(band.high) : null;
  const mean = typeof band.mean === "number" ? Math.round(band.mean) : null;
  const anchor = mean ?? low ?? high;
  if (anchor === null) return missingMessage;
  if (low !== null && high !== null && Math.abs(low - high) > 1) {
    return `${prefix}: ${low} to ${high} minutes`;
  }
  return `${prefix}: about ${anchor} minutes`;
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

function DetailList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;

  return (
    <div className="rounded-[22px] border border-border bg-surfaceAlt/45 p-4">
      <p className="section-kicker">{title}</p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <p key={item} className="text-sm leading-6 text-muted">
            {item}
          </p>
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
  const primarySummary = stripRecommendedPrefix(conciseSummary ?? explanation);
  const mainRisk = (keyRisks.length ? keyRisks : ["No major operational risk was flagged in the short evaluation bundle."])[0];
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
      ? "High"
      : confidenceSummary?.confidence_level === "moderate"
        ? "Moderate"
        : confidenceSummary?.confidence_level === "low"
          ? "Low"
          : "Pending";
  const whyThisFitsLead =
    uniqueCopy([explanation, searchPatternReason, searchPatternFitSummary], 1)[0] ??
    "The recommendation fits the current mission geometry, fleet profile, and operational conditions.";
  const whyThisFitsPoints = uniqueCopy(
    [searchPatternFitSummary, searchPatternReason, searchPatternSummary, missionAreaSummary, assetPackage?.operator_summary],
    3,
  ).filter((item) => normalizeCopy(item) !== normalizeCopy(whyThisFitsLead));
  const planningWatchItems = uniqueCopy(
    [
      ...feasibilityWarnings.map((item) => item.summary ?? item.title ?? ""),
      ...keyRisks,
      feasibilitySummary?.operator_summary,
      feasibilitySummary?.next_watch,
    ],
    4,
  );
  const alternativeSummary =
    topAlternativeSummary ?? "No close alternative was returned in this evaluation bundle.";

  return (
    <div className="panel-subtle p-5 md:p-6">
      <p className="section-kicker">Recommended plan</p>
      <h3 className="mt-3 max-w-4xl text-[28px] font-semibold leading-tight text-white">{primarySummary}</h3>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.18fr_0.82fr]">
        <div className="space-y-4">
          <div className="rounded-[24px] border border-border bg-white/[0.04] p-5">
            <p className="section-kicker">Why this fits</p>
            <p className="mt-3 text-sm leading-7 text-white/92">{whyThisFitsLead}</p>
            <div className="mt-4 space-y-2">
              {whyThisFitsPoints.map((item) => (
                <p key={item} className="text-sm leading-6 text-muted">
                  {item}
                </p>
              ))}
            </div>
            <div className="mt-5 rounded-[20px] border border-border/70 bg-surfaceAlt/55 p-4">
              <p className="micro-label">Next action</p>
              <p className="mt-2 text-sm leading-6 text-white">
                Continue to save the mission plan, compare it against alternatives, or launch a simulation.
              </p>
            </div>
          </div>

          <div className="rounded-[24px] border border-border bg-surfaceAlt/50 p-5">
            <p className="section-kicker">Best alternative</p>
            <p className="mt-3 text-sm leading-7 text-white/92">{alternativeSummary}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[24px] border border-border bg-surfaceAlt/50 p-5">
            <p className="section-kicker">Expected timeline</p>
            <p className="mt-3 text-lg font-semibold text-white">{patternTitle}</p>
            <div className="mt-4 space-y-2">
              <p className="text-sm leading-6 text-white/92">
                {formatMinuteWindow(firstCandidateBand, "First candidate", "First candidate window not available.")}
              </p>
              <p className="text-sm leading-6 text-muted">
                {formatMinuteWindow(confirmedBand, "Confirmed contact", "Confirmed-contact window not available.")}
              </p>
            </div>
          </div>

          <div className="rounded-[24px] border border-border bg-surfaceAlt/50 p-5">
            <p className="section-kicker">Confidence</p>
            <p className="mt-3 text-lg font-semibold text-white">{confidenceLabel}</p>
            <p className="mt-3 text-sm leading-7 text-muted">
              {confidenceSummary?.confidence_reason ?? "Confidence notes were not returned for this recommendation."}
            </p>
          </div>

          <div className="rounded-[24px] border border-danger/20 bg-danger/10 p-5">
            <p className="section-kicker">Main risk</p>
            <p className="mt-3 text-sm leading-7 text-white/92">{mainRisk}</p>
          </div>
        </div>
      </div>

      <div className="mt-5">
        <CollapsiblePanel
          title="Technical assumptions"
          description="Open the assumptions, watch items, and structured model notes behind this recommendation."
          defaultOpen={false}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <DetailList title="Key tradeoffs" items={keyTradeoffs} />
            <DetailList title="Planning watch items" items={planningWatchItems} />
            <DetailRows
              title="Recommendation snapshot"
              record={{
                search_pattern: patternTitle,
                drone_count: drones,
                reserve_threshold_pct: reserveThreshold,
                team_coordination_style: teamCoordinationLabel,
              }}
            />
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
