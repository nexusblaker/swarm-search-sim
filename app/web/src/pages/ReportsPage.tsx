import { useState } from "react";

import { api } from "@/api/client";
import { useReports } from "@/api/hooks";
import { ArtifactLink } from "@/components/ui/ArtifactLink";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Panel } from "@/components/ui/Panel";
import { formatTimestamp } from "@/lib/format";

export function ReportsPage() {
  const { data, isLoading, error } = useReports();
  const reports = data?.items ?? [];
  const [selectedId, setSelectedId] = useState("");
  const selected = reports.find((report) => report.id === selectedId) ?? reports[0];

  if (isLoading) return <LoadingState label="Loading reports..." />;
  if (error) return <ErrorState message={(error as Error).message} />;
  if (reports.length === 0) return <EmptyState title="No reports indexed yet" body="Reports appear here after mission runs, reviews, plans, or comparisons generate them." />;

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr]">
      <Panel title="Report Index" description="Indexed HTML reports across the planning and evaluation workflow.">
        <DataTable
          columns={["Report", "Owner", "Type", "Created"]}
          rows={reports.map((report) => [
            <button type="button" onClick={() => setSelectedId(report.id)} className="font-medium hover:text-accent">
              {report.id}
            </button>,
            `${report.owner_type}:${report.owner_id ?? "n/a"}`,
            report.report_type,
            formatTimestamp(report.created_at),
          ])}
        />
      </Panel>
      <Panel title="Report Details" description="Open the selected report in a new tab or inspect its metadata.">
        <p className="text-sm text-white">Report ID: {selected.id}</p>
        <p className="mt-2 text-sm text-muted">Owner: {selected.owner_type}:{selected.owner_id ?? "n/a"}</p>
        <div className="mt-4">
          <ArtifactLink href={`${api.baseUrl}/reports/${selected.id}/content`} label="Open HTML Report" />
        </div>
        <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
          {JSON.stringify(selected.summary_json, null, 2)}
        </pre>
      </Panel>
    </div>
  );
}
