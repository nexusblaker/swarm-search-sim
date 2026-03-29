import { Link } from "react-router-dom";

import { useDashboardSummary } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

export function DashboardPage() {
  const { data, isLoading, error } = useDashboardSummary();

  if (isLoading) return <LoadingState label="Loading mission dashboard..." />;
  if (error) return <ErrorState message={(error as Error).message} />;
  if (!data) return <EmptyState title="Dashboard unavailable" body="Backend summary data is not available yet." />;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Start here"
        title="Mission planning at a glance"
        description="See what already exists, where the team should go next, and what activity has happened most recently across planning, monitoring, review, and reporting."
        actions={
          <>
            <Link to="/plans" className="primary-button">
              Create mission plan
            </Link>
            <Link to="/library" className="secondary-button">
              Browse doctrine library
            </Link>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Scenarios" value={data.counts.scenarios} hint="Saved search environments and assumptions." />
        <MetricCard label="Mission Plans" value={data.counts.plans} hint="Reusable planning workspaces." emphasis="accent" />
        <MetricCard label="Comparisons" value={data.counts.comparisons} hint="Saved pre-mission evaluations." />
        <MetricCard label="Runs" value={data.counts.runs} hint={`${data.active_runs} currently active`} />
        <MetricCard label="Reviews" value={data.counts.reviews} hint="After-action learning captured." />
        <MetricCard label="Reports" value={data.counts.reports} hint="Indexed exports and artifacts." />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.95fr]">
        <Panel
          eyebrow="Onboarding"
          title="Recommended next steps"
          description="The product surfaces the next useful action automatically so operators can move through the workflow without needing a walkthrough."
        >
          <div className="grid gap-4">
            {data.suggested_actions.map((action) => (
              <Link
                key={action.route}
                to={action.route}
                className="rounded-[24px] border border-border bg-surfaceAlt/60 p-5 transition hover:border-accentStrong/40 hover:bg-surfaceAlt/80"
              >
                <p className="section-kicker">Recommended action</p>
                <div className="mt-2 flex items-center justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-white">{action.label}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted">{action.description}</p>
                  </div>
                  <span className="primary-button whitespace-nowrap px-4 py-2.5">Open</span>
                </div>
              </Link>
            ))}
          </div>
        </Panel>

        <Panel
          eyebrow="System state"
          title="Current platform posture"
          description="Quick operational context for demos and first-launch orientation."
        >
          <div className="grid gap-4">
            <div className="panel-subtle p-5">
              <p className="section-kicker">Backend health</p>
              <div className="mt-3 flex items-center gap-3">
                <StatusBadge status={data.backend_status} />
                <span className="text-sm leading-6 text-muted">
                  {data.active_runs} active runs, {data.completed_runs} completed runs, {data.queued_jobs} queued jobs
                </span>
              </div>
            </div>
            <div className="panel-subtle p-5">
              <p className="section-kicker">Workflow</p>
              <p className="mt-3 text-sm leading-7 text-muted">
                This product is optimized for a clear SAR evaluation loop: plan, compare, launch, monitor,
                replay, review, and report.
              </p>
            </div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel
          eyebrow="Recent activity"
          title="What changed most recently"
          description="Recent runs, reports, and reviews appear here so the latest operational work is always visible."
        >
          {data.recent_activity.length === 0 ? (
            <EmptyState
              title="No recent activity yet"
              body="Create a mission plan from the doctrine library, compare it, and launch a monitored run to populate the activity stream."
            />
          ) : (
            <div className="space-y-3">
              {data.recent_activity.map((activity) => (
                <div key={`${activity.kind}-${activity.id}`} className="panel-subtle p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">{activity.title}</p>
                      <p className="mt-1 text-sm leading-6 text-muted">{activity.subtitle}</p>
                    </div>
                    <div className="text-right">
                      {activity.status ? <StatusBadge status={activity.status} /> : null}
                      <p className="mt-2 text-xs uppercase tracking-[0.14em] text-muted">
                        {formatTimestamp(activity.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel
          eyebrow="Reports"
          title="Latest exported outputs"
          description="Recent indexed artifacts are surfaced here so operators can jump directly into reporting and review."
        >
          {data.recent_reports.length === 0 ? (
            <EmptyState
              title="No reports yet"
              body="Complete a run and generate an after-action review to create reports worth sharing."
            />
          ) : (
            <DataTable
              columns={["Report", "Owner", "Type", "Created"]}
              rows={data.recent_reports.map((report) => [
                report.id,
                `${report.owner_type}:${report.owner_id ?? "n/a"}`,
                report.report_type,
                formatTimestamp(report.created_at),
              ])}
            />
          )}
        </Panel>
      </div>

      <Panel
        eyebrow="Monitoring"
        title="Recent mission runs"
        description="The latest mission runs stay visible on the dashboard so operators can jump back into monitoring or review without hunting through history."
      >
        {data.recent_runs.length === 0 ? (
          <EmptyState
            title="No runs launched yet"
            body="Use Mission Plans or Plan Comparison to launch a monitored simulation run."
            action={
              <Link to="/mission-control" className="primary-button">
                Open mission control
              </Link>
            }
          />
        ) : (
          <DataTable
            columns={["Run", "Status", "Plan", "Strategy", "Updated"]}
            rows={data.recent_runs.map((run) => [
              <span className="font-medium">{run.id}</span>,
              <StatusBadge status={run.status} />,
              run.plan_id ?? "ad hoc",
              String(run.summary_json.strategy ?? "n/a"),
              formatTimestamp(run.updated_at),
            ])}
          />
        )}
      </Panel>
    </div>
  );
}
