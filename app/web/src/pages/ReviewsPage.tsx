import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useReports, useReviews, useRuns } from "@/api/hooks";
import { ArtifactLink } from "@/components/ui/ArtifactLink";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { Panel } from "@/components/ui/Panel";
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
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Reviews" value={reviews.length} />
        <MetricCard label="Completed Runs" value={completedRuns.length} />
        <MetricCard label="Linked Reports" value={reviews.filter((review) => review.report_id).length} />
        <MetricCard label="Latest Outcome" value={String(selected?.summary_json?.mission_success ?? "n/a")} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_1fr]">
        <Panel title="After Action Review Index" description="Structured review objects linked to runs, reports, and alternate plan analysis.">
          {reviews.length === 0 ? (
            <EmptyState title="No reviews yet" body="Generate an AAR from a completed run to capture mission outcome and findings." />
          ) : (
            <DataTable
              columns={["Review", "Run", "Plan", "Created"]}
              rows={reviews.map((review) => [
                <button
                  type="button"
                  onClick={() => setSelectedId(review.id)}
                  className="text-left font-medium hover:text-accent"
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

        <Panel title="Generate Review" description="Create a new after-action review from a completed mission run.">
          <label className="space-y-2 text-sm text-muted">
            <span>Completed run</span>
            <select
              className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
            >
              <option value="">Select a run</option>
              {completedRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.id}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={() => createReview.mutate()}
            className="mt-5 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300"
          >
            Generate AAR
          </button>
        </Panel>
      </div>

      {selected && (
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.95fr]">
          <Panel title="Review Summary" description="Outcome, deviation from recommendation, and asset utilization summary.">
            <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
              {JSON.stringify(selected.summary_json, null, 2)}
            </pre>
            <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
              {JSON.stringify(selected.alternate_plan_json, null, 2)}
            </pre>
          </Panel>

          <Panel title="Timeline And Links" description="Interventions, report artifacts, and linked run metadata.">
            <div className="space-y-3">
              <StatusBadge status={runQuery.data?.status ?? "completed"} />
              {reviewReport && (
                <ArtifactLink href={`${api.baseUrl}/reports/${reviewReport.id}/content`} label="Open Review Report" />
              )}
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
                {JSON.stringify(selected.timeline_json, null, 2)}
              </pre>
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
