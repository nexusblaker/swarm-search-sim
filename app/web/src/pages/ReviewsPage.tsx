import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useReports, useReviews, useRuns } from "@/api/hooks";
import type {
  BatteryLifecycleSummary,
  ReviewSummaryRecord,
  ReviewTimelineRecord,
  SensingLifecycleSummary,
} from "@/api/types";
import { EventTimeline } from "@/components/mission/EventTimeline";
import { ArtifactLink } from "@/components/ui/ArtifactLink";
import { DataTable } from "@/components/ui/DataTable";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RiskIndicator } from "@/components/ui/RiskIndicator";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

export function ReviewsPage() {
  const { data: reviewsData, isLoading, error } = useReviews();
  const { data: runsData } = useRuns();
  const { data: reportsData } = useReports();
  const reviews = reviewsData?.items ?? [];
  const completedRuns = (runsData?.items ?? []).filter((run) => run.status === "completed");
  const reports = reportsData?.items ?? [];
  const [selectedId, setSelectedId] = useState("");
  const [runId, setRunId] = useState("");

  const selected = useMemo(
    () => reviews.find((review) => review.id === selectedId) ?? reviews[0],
    [reviews, selectedId],
  );

  const reviewReport = reports.find((report) => report.id === selected?.report_id);
  const runQuery = useQuery({
    queryKey: ["run", selected?.run_id],
    queryFn: () => api.run(selected!.run_id),
    enabled: Boolean(selected?.run_id),
  });

  const createReview = useMutation({
    mutationFn: () => api.createReviewFromRun(runId),
  });

  if (isLoading) return <LoadingState label="Loading after-action reviews..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  const summary = (selected?.summary_json ?? {}) as ReviewSummaryRecord;
  const batteryLifecycle = (summary.battery_lifecycle ?? {}) as BatteryLifecycleSummary;
  const sensingLifecycle = (summary.sensing_lifecycle ?? {}) as SensingLifecycleSummary;
  const timeline = (selected?.timeline_json ?? {}) as ReviewTimelineRecord;
  const actualOutcome = summary.actual_outcome ?? {};
  const actualMetrics = (actualOutcome.metrics as Record<string, unknown> | undefined) ?? {};

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operational review"
        title="After-action review"
        description="Understand what happened, why it mattered, and what should be learned from the completed mission. This page is the review center for replay-backed evaluation."
        actions={
          <button type="button" onClick={() => createReview.mutate()} className="primary-button">
            Generate AAR
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Reviews" value={reviews.length} />
        <MetricCard label="Completed runs" value={completedRuns.length} />
        <MetricCard label="Linked reports" value={reviews.filter((review) => review.report_id).length} />
        <MetricCard
          label="Reserve policy"
          value={batteryLifecycle.reserve_preset?.replaceAll("_", " ") ?? "n/a"}
          emphasis="accent"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <Panel
          eyebrow="Review index"
          title="Stored after-action reviews"
          description="Open an existing review or generate a new one from a completed run."
        >
          {reviews.length === 0 ? (
            <EmptyState
              title="No reviews yet"
              body="Generate an AAR from a completed run to capture mission outcome and lessons learned."
            />
          ) : (
            <DataTable
              columns={["Review", "Run", "Plan", "Created"]}
              rows={reviews.map((review) => [
                <button
                  type="button"
                  onClick={() => setSelectedId(review.id)}
                  className="text-left font-medium hover:text-accentStrong"
                >
                  {review.name}
                </button>,
                review.run_id,
                review.plan_id ?? "ad hoc",
                formatTimestamp(review.created_at),
              ])}
            />
          )}
        </Panel>

        <Panel
          eyebrow="Generation"
          title="Create a new review"
          description="Primary action: pick a completed run and generate an after-action review so replay, findings, and reporting remain linked."
        >
          <label>
            <span className="field-label">Completed run</span>
            <select className="field-input" value={runId} onChange={(event) => setRunId(event.target.value)}>
              <option value="">Select a run</option>
              {completedRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.id}
                </option>
              ))}
            </select>
          </label>
        </Panel>
      </div>

      {selected ? (
        <>
          <div className="grid gap-6 xl:grid-cols-3">
            <RiskIndicator label="Mission status" value={String(actualOutcome.status ?? "n/a")} tone="good" />
            <RiskIndicator
              label="Mission continuity"
              value={String(batteryLifecycle.mission_continuity_impact ?? "n/a")}
              tone="warning"
            />
            <RiskIndicator
              label="Sensing workflow"
              value={String(sensingLifecycle.operator_summary ?? "n/a")}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
            <Panel
              eyebrow="Outcome summary"
              title={selected.name}
              description="Use this view to explain the mission outcome, the fleet rotation burden, and what the team should take away from the run."
            >
              <div className="space-y-4">
                <div className="panel-subtle p-4">
                  <p className="section-kicker">Mission narrative</p>
                  <p className="mt-3 text-sm leading-6 text-white/90">
                    {summary.mission_timeline ?? "Generated from replay, events, and intervention history."}
                  </p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <ReviewMetric label="Returns to base" value={batteryLifecycle.return_to_base_count ?? 0} />
                  <ReviewMetric label="Service cycles completed" value={batteryLifecycle.recharge_completed_count ?? 0} />
                  <ReviewMetric label="Redeployments" value={batteryLifecycle.redeploy_count ?? 0} />
                  <ReviewMetric label="Coverage gaps" value={batteryLifecycle.coverage_gap_count ?? 0} />
                </div>
                <div className="panel-subtle p-4">
                  <p className="section-kicker">Battery rotation summary</p>
                  <p className="mt-3 text-sm leading-6 text-white/90">
                    {batteryLifecycle.asset_utilization_summary ?? "No fleet rotation summary available."}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-muted">
                    {batteryLifecycle.mission_continuity_impact ?? "No mission continuity note available."}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-white/90">
                    Battery margin: min {String(batteryLifecycle.battery_margin_summary?.minimum_margin ?? "n/a")} /
                    avg {String(batteryLifecycle.battery_margin_summary?.average_margin ?? "n/a")}
                  </p>
                </div>
                <div className="panel-subtle p-4">
                  <p className="section-kicker">Sensing workflow summary</p>
                  <p className="mt-3 text-sm leading-6 text-white/90">
                    {sensingLifecycle.operator_summary ?? "No sensing workflow summary available."}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-muted">
                    {sensingLifecycle.inspection_burden_summary ?? "No inspection burden note available."}
                  </p>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <ReviewMetric label="Possible contacts" value={sensingLifecycle.candidate_detection_count ?? 0} />
                    <ReviewMetric label="Inspections started" value={sensingLifecycle.inspection_initiated_count ?? 0} />
                    <ReviewMetric label="Inspection passes" value={sensingLifecycle.inspection_pass_count ?? 0} />
                    <ReviewMetric label="Rejected false alarms" value={sensingLifecycle.false_positive_count ?? 0} />
                  </div>
                </div>
                <div className="panel-subtle p-4">
                  <p className="section-kicker">Alternate plan summary</p>
                  <p className="mt-3 text-sm leading-6 text-white/90">
                    {String(selected.alternate_plan_json.summary ?? "No alternate-plan analysis was captured.")}
                  </p>
                </div>
              </div>
            </Panel>

            <div className="space-y-6">
              <DetailPanel
                title="Linked objects"
                items={[
                  { label: "Run", value: selected.run_id },
                  { label: "Plan", value: selected.plan_id ?? "n/a" },
                  { label: "Comparison", value: selected.comparison_id ?? "n/a" },
                  { label: "Report", value: selected.report_id ?? "n/a" },
                ]}
              />
              <Panel
                eyebrow="Artifacts"
                title="Review links"
                description="Open the linked report or inspect the run status associated with this review."
              >
                <div className="flex flex-wrap items-center gap-3">
                  <StatusBadge status={runQuery.data?.status ?? "completed"} />
                  {reviewReport ? (
                    <ArtifactLink href={`${api.baseUrl}/reports/${reviewReport.id}/content`} label="Open review report" />
                  ) : null}
                </div>
              </Panel>
              <Panel
                eyebrow="Mission metrics"
                title="Captured outcome metrics"
                description="These values summarize what the completed mission achieved."
              >
                <div className="space-y-3">
                  <ReviewMetric label="Mission success" value={String(actualMetrics.mission_success ?? "n/a")} />
                  <ReviewMetric label="Area covered (%)" value={String(actualMetrics.area_covered_pct ?? "n/a")} />
                  <ReviewMetric label="Battery used" value={String(actualMetrics.battery_used ?? "n/a")} />
                  <ReviewMetric
                    label="Average active search drones"
                    value={String(actualMetrics.average_active_search_drones ?? "n/a")}
                  />
                </div>
              </Panel>
            </div>
          </div>

          <Panel
            eyebrow="Timeline"
            title="Review timeline"
            description="The review timeline carries the key events that shaped the mission outcome, battery rotation, and cue-to-confirm sensing story."
          >
            {timeline.key_events?.length ? (
              <EventTimeline events={timeline.key_events.slice(0, 16)} />
            ) : (
              <EmptyState title="No timeline captured" body="This review did not record key events." />
            )}
          </Panel>

          <details className="panel-surface p-6">
            <summary className="cursor-pointer text-xs uppercase tracking-[0.14em] text-muted">
              Technical details
            </summary>
            <pre className="mt-4 whitespace-pre-wrap text-xs leading-6 text-muted">
              {JSON.stringify(summary, null, 2)}
            </pre>
          </details>
        </>
      ) : null}
    </div>
  );
}

function ReviewMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-[18px] border border-border/70 bg-surfaceAlt/55 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-2 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
