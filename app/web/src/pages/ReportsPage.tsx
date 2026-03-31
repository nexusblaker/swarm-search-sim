import { useMemo, useState } from "react";

import { api } from "@/api/client";
import { useReports } from "@/api/hooks";
import type { BatteryLifecycleSummary, ReportSummaryRecord } from "@/api/types";
import { ArtifactLink } from "@/components/ui/ArtifactLink";
import { DataTable } from "@/components/ui/DataTable";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { formatTimestamp } from "@/lib/format";

export function ReportsPage() {
  const { data, isLoading, error } = useReports();
  const reports = data?.items ?? [];
  const [selectedId, setSelectedId] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("all");
  const selected = reports.find((report) => report.id === selectedId) ?? reports[0];

  const filteredReports = useMemo(
    () => reports.filter((report) => ownerFilter === "all" || report.owner_type === ownerFilter),
    [ownerFilter, reports],
  );

  if (isLoading) return <LoadingState label="Loading reports..." />;
  if (error) return <ErrorState message={(error as Error).message} />;
  if (reports.length === 0) {
    return (
      <EmptyState
        title="No reports indexed yet"
        body="Reports appear here after mission runs, reviews, plans, or comparisons generate them."
      />
    );
  }

  const summary = (selected.summary_json ?? {}) as ReportSummaryRecord;
  const batteryLifecycle = (summary.battery_lifecycle ?? {}) as BatteryLifecycleSummary;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Exports and artifacts"
        title="Reports"
        description="Browse indexed HTML reports, filter by owner type, and move directly from plans, runs, and reviews into shareable outputs."
      />

      <Panel
        eyebrow="Filters"
        title="Report browser"
        description="Use owner type to narrow the browser to the reports relevant to the workflow you are presenting."
      >
        <div className="max-w-sm">
          <label>
            <span className="field-label">Owner type</span>
            <select className="field-input" value={ownerFilter} onChange={(event) => setOwnerFilter(event.target.value)}>
              <option value="all">All owner types</option>
              {Array.from(new Set(reports.map((report) => report.owner_type))).map((ownerType) => (
                <option key={ownerType} value={ownerType}>
                  {ownerType}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      <div className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
        <Panel
          eyebrow="Index"
          title="Indexed reports"
          description="Open a report to inspect its metadata, linkage, and export path."
        >
          <DataTable
            columns={["Report", "Owner", "Type", "Created"]}
            rows={filteredReports.map((report) => [
              <button type="button" onClick={() => setSelectedId(report.id)} className="font-medium hover:text-accentStrong">
                {report.id}
              </button>,
              `${report.owner_type}:${report.owner_id ?? "n/a"}`,
              report.report_type,
              formatTimestamp(report.created_at),
            ])}
          />
        </Panel>

        <div className="space-y-6">
          <DetailPanel
            title="Selected report"
            items={[
              { label: "Report ID", value: selected.id },
              { label: "Owner", value: `${selected.owner_type}:${selected.owner_id ?? "n/a"}` },
              { label: "Type", value: selected.report_type },
              { label: "Created", value: formatTimestamp(selected.created_at) },
              { label: "Run phase", value: summary.run_phase ?? "n/a" },
            ]}
          />
          <Panel
            eyebrow="Lifecycle summary"
            title="Report highlights"
            description="This summary surfaces the main battery lifecycle and continuity points before you open the full HTML export."
          >
            <ArtifactLink href={`${api.baseUrl}/reports/${selected.id}/content`} label="Open HTML report" />
            <div className="mt-5 space-y-4">
              <div className="panel-subtle p-4">
                <p className="section-kicker">Reserve policy</p>
                <p className="mt-3 text-sm leading-6 text-white/90">
                  {batteryLifecycle.reserve_preset?.replaceAll("_", " ") ?? "No reserve policy captured."}
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <ReportMetric label="Returns to base" value={batteryLifecycle.return_to_base_count ?? "n/a"} />
                <ReportMetric label="Service cycles completed" value={batteryLifecycle.recharge_completed_count ?? "n/a"} />
                <ReportMetric label="Redeployments" value={batteryLifecycle.redeploy_count ?? "n/a"} />
                <ReportMetric label="Coverage gaps" value={batteryLifecycle.coverage_gap_count ?? "n/a"} />
              </div>
              <div className="panel-subtle p-4">
                <p className="section-kicker">Mission continuity</p>
                <p className="mt-3 text-sm leading-6 text-white/90">
                  {batteryLifecycle.mission_continuity_impact ?? "No continuity note available for this report."}
                </p>
              </div>
            </div>
          </Panel>

          <details className="panel-surface p-6">
            <summary className="cursor-pointer text-xs uppercase tracking-[0.14em] text-muted">
              Technical details
            </summary>
            <pre className="mt-4 whitespace-pre-wrap text-xs leading-6 text-muted">
              {JSON.stringify(summary, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    </div>
  );
}

function ReportMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-[18px] border border-border/70 bg-surfaceAlt/55 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-2 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
