import { useMemo, useState } from "react";

import { api } from "@/api/client";
import { useReports } from "@/api/hooks";
import type { BatteryLifecycleSummary, ReportSummaryRecord, SensingLifecycleSummary } from "@/api/types";
import { ArtifactLink } from "@/components/ui/ArtifactLink";
import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel";
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
  const sensingLifecycle = (summary.sensing_lifecycle ?? {}) as SensingLifecycleSummary;
  const reportTitle =
    selected.owner_type === "review"
      ? "After-action report"
      : selected.owner_type === "run"
        ? "Run summary"
        : selected.owner_type === "plan"
          ? "Mission brief"
          : "Mission report";

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Exports and artifacts"
        title="Reports"
        description="Browse mission briefs, run summaries, and after-action reports with cleaner titles and easier export language."
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
          description="Open a report to inspect its summary, export actions, and linked mission context."
        >
          <DataTable
            columns={["Report", "Owner", "Type", "Created"]}
            rows={filteredReports.map((report) => [
              <button type="button" onClick={() => setSelectedId(report.id)} className="font-medium hover:text-accentStrong">
                {report.owner_type === "review"
                  ? "After-action report"
                  : report.owner_type === "run"
                    ? "Run summary"
                    : report.owner_type === "plan"
                      ? "Mission brief"
                      : report.id}
              </button>,
              `${report.owner_type}:${report.owner_id ?? "n/a"}`,
              report.report_type.replaceAll("_", " "),
              formatTimestamp(report.created_at),
            ])}
          />
        </Panel>

        <div className="space-y-6">
          <DetailPanel
            title={reportTitle}
            items={[
              { label: "Report ID", value: selected.id },
              { label: "Owner", value: `${selected.owner_type}:${selected.owner_id ?? "n/a"}` },
              { label: "Type", value: selected.report_type.replaceAll("_", " ") },
              { label: "Created", value: formatTimestamp(selected.created_at) },
              { label: "Run phase", value: summary.run_phase ?? "n/a" },
            ]}
          />
          <Panel
            eyebrow="Export actions"
            title="Report highlights"
            description="Start with the readable export actions, then review the operational summary before opening the full HTML report."
          >
            <div className="flex flex-wrap gap-3">
              <ArtifactLink
                href={`${api.baseUrl}/reports/${selected.id}/content`}
                label={
                  selected.owner_type === "review"
                    ? "Export after-action report"
                    : selected.owner_type === "run"
                      ? "Export run summary"
                      : selected.owner_type === "plan"
                        ? "Export mission brief"
                        : "Open report"
                }
              />
              <ArtifactLink href={`${api.baseUrl}/reports/${selected.id}/content`} label="Download technical report" />
            </div>
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
              <div className="panel-subtle p-4">
                <p className="section-kicker">Sensing workflow</p>
                <p className="mt-3 text-sm leading-6 text-white/90">
                  {sensingLifecycle.operator_summary ?? "No sensing workflow summary available for this report."}
                </p>
                <p className="mt-3 text-sm leading-6 text-muted">
                  {sensingLifecycle.inspection_burden_summary ?? "No inspection burden note available."}
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <ReportMetric label="Possible contacts" value={sensingLifecycle.candidate_detection_count ?? "n/a"} />
                  <ReportMetric label="Inspection passes" value={sensingLifecycle.inspection_pass_count ?? "n/a"} />
                  <ReportMetric label="Confirmed contacts" value={sensingLifecycle.confirmed_detection_count ?? "n/a"} />
                  <ReportMetric label="Rejected false alarms" value={sensingLifecycle.false_positive_count ?? "n/a"} />
                </div>
              </div>
            </div>
          </Panel>

          <CollapsiblePanel
            title="Technical details"
            description="Open the structured report summary behind this export view."
            defaultOpen={false}
          >
            <pre className="whitespace-pre-wrap text-xs leading-6 text-muted">
              {JSON.stringify(summary, null, 2)}
            </pre>
          </CollapsiblePanel>
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
