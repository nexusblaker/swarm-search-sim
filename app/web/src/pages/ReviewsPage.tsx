import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useReports, useReviews, useRuns } from "@/api/hooks";
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
        <MetricCard label="Latest outcome" value={String(selected?.summary_json?.mission_success ?? "n/a")} emphasis="accent" />
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
            <RiskIndicator label="Mission success" value={String(selected.summary_json?.mission_success ?? "n/a")} tone="good" />
            <RiskIndicator label="Deviation from recommendation" value={String(selected.summary_json?.deviation_from_recommendation ?? "n/a")} tone="warning" />
            <RiskIndicator label="Battery and comms risk" value={String(selected.summary_json?.battery_comms_risk ?? "n/a")} />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.14fr_0.96fr]">
            <Panel
              eyebrow="Outcome summary"
              title={selected.name}
              description="Use this view to explain the mission outcome, the risk picture, and what the team should take away from the run."
            >
              <pre className="whitespace-pre-wrap text-xs leading-6 text-muted">{JSON.stringify(selected.summary_json, null, 2)}</pre>
              <div className="mt-5 rounded-[22px] border border-border bg-surfaceAlt/55 p-4">
                <p className="section-kicker">Alternate-plan summary</p>
                <pre className="mt-3 whitespace-pre-wrap text-xs leading-6 text-muted">
                  {JSON.stringify(selected.alternate_plan_json, null, 2)}
                </pre>
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
            </div>
          </div>

          <Panel
            eyebrow="Timeline"
            title="Review timeline"
            description="The review timeline carries the key events that shaped the mission outcome."
          >
            <pre className="whitespace-pre-wrap text-xs leading-6 text-muted">{JSON.stringify(selected.timeline_json, null, 2)}</pre>
          </Panel>
        </>
      ) : null}
    </div>
  );
}
