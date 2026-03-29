import { Link } from "react-router-dom";

import { useComparisons, useHealth, usePlans, useReports, useReviews, useRuns, useScenarios } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

export function DashboardPage() {
  const healthQuery = useHealth();
  const scenariosQuery = useScenarios();
  const plansQuery = usePlans();
  const comparisonsQuery = useComparisons();
  const runsQuery = useRuns();
  const reviewsQuery = useReviews();
  const reportsQuery = useReports();

  const isLoading = [
    healthQuery,
    scenariosQuery,
    plansQuery,
    comparisonsQuery,
    runsQuery,
    reviewsQuery,
    reportsQuery,
  ].some((entry) => entry.isLoading);
  const error = [
    healthQuery.error,
    scenariosQuery.error,
    plansQuery.error,
    comparisonsQuery.error,
    runsQuery.error,
    reviewsQuery.error,
    reportsQuery.error,
  ].find(Boolean) as Error | undefined;

  if (isLoading) return <LoadingState label="Loading dashboard..." />;
  if (error) return <ErrorState message={error.message} />;

  const recentRuns = runsQuery.data?.items.slice(0, 5) ?? [];
  const recentReports = reportsQuery.data?.items.slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Scenarios" value={scenariosQuery.data?.items.length ?? 0} />
        <MetricCard label="Mission Plans" value={plansQuery.data?.items.length ?? 0} />
        <MetricCard label="Comparisons" value={comparisonsQuery.data?.items.length ?? 0} />
        <MetricCard label="Runs" value={runsQuery.data?.items.length ?? 0} />
        <MetricCard label="Reviews" value={reviewsQuery.data?.items.length ?? 0} />
        <MetricCard label="Reports" value={reportsQuery.data?.items.length ?? 0} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
        <Panel title="Recent Runs" description="Latest simulated missions and their lifecycle state.">
          <DataTable
            columns={["Run", "Status", "Plan", "Updated"]}
            rows={recentRuns.map((run) => [
              <span className="font-medium">{run.id}</span>,
              <StatusBadge status={run.status} />,
              run.plan_id ?? "ad hoc",
              formatTimestamp(run.updated_at),
            ])}
          />
        </Panel>
        <Panel title="Quick Actions" description="Common operator tasks for planning and review.">
          <div className="grid gap-3 md:grid-cols-2">
            {[
              { to: "/plans", label: "Create Mission Plan" },
              { to: "/comparisons", label: "Run Plan Comparison" },
              { to: "/mission-control", label: "Monitor Mission" },
              { to: "/reviews", label: "Open After Action Review" },
            ].map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="rounded-2xl border border-border bg-surfaceAlt/70 px-4 py-5 text-sm font-medium text-white transition hover:border-accent/40 hover:text-accent"
              >
                {item.label}
              </Link>
            ))}
          </div>
          <pre className="mt-5 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
            {JSON.stringify(healthQuery.data, null, 2)}
          </pre>
        </Panel>
      </div>

      <Panel title="Recent Reports" description="Indexed outputs across plans, comparisons, reviews, and runs.">
        <DataTable
          columns={["Report", "Owner", "Type", "Created"]}
          rows={recentReports.map((report) => [
            report.id,
            `${report.owner_type}:${report.owner_id ?? "n/a"}`,
            report.report_type,
            formatTimestamp(report.created_at),
          ])}
        />
      </Panel>
    </div>
  );
}
