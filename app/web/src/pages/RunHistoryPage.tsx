import { useMemo, useState } from "react";

import { useRuns } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

export function RunHistoryPage() {
  const { data, isLoading, error } = useRuns(5000);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [selectedId, setSelectedId] = useState("");
  const runs = data?.items ?? [];

  const filteredRuns = useMemo(
    () =>
      runs.filter((run) => {
        const matchesStatus = status === "all" || run.status === status;
        const haystack = `${run.id} ${run.plan_id ?? ""} ${run.comparison_id ?? ""} ${run.summary_json.strategy ?? ""} ${run.summary_json.scenario_family ?? ""}`.toLowerCase();
        return matchesStatus && haystack.includes(search.toLowerCase());
      }),
    [runs, search, status],
  );
  const selected = filteredRuns.find((run) => run.id === selectedId) ?? filteredRuns[0];

  if (isLoading) return <LoadingState label="Loading run history..." />;
  if (error) return <ErrorState message={(error as Error).message} />;
  if (runs.length === 0) {
    return <EmptyState title="No runs yet" body="Launch a monitored mission to populate run history." />;
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Mission ledger"
        title="Run history"
        description="Browse active and completed runs, filter by status or source, and inspect the run context without leaving the history workflow."
      />

      <div className="grid gap-6 xl:grid-cols-[1.04fr_0.96fr]">
        <Panel
          eyebrow="Search"
          title="Filter runs"
          description="Primary action: narrow the list to the mission family, plan, or status you care about, then inspect the selected run in the detail panel."
        >
          <div className="grid gap-3 md:grid-cols-[1fr_220px]">
            <input className="field-input" placeholder="Search runs, plans, strategies, or scenario families" value={search} onChange={(event) => setSearch(event.target.value)} />
            <select className="field-input" value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="all">All statuses</option>
              {Array.from(new Set(runs.map((run) => run.status))).map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
          <div className="mt-5">
            <DataTable
              columns={["Run", "Status", "Source", "Strategy", "Progress", "Updated"]}
              rows={filteredRuns.map((run) => [
                <button type="button" onClick={() => setSelectedId(run.id)} className="text-left font-medium hover:text-accentStrong">
                  {run.id}
                </button>,
                <StatusBadge status={run.status} />,
                run.plan_id ? `plan:${run.plan_id}` : run.comparison_id ? `comparison:${run.comparison_id}` : run.scenario_id,
                String(run.summary_json.strategy ?? "n/a"),
                <div className="min-w-40 space-y-2">
                  <ProgressBar value={run.job?.progress ?? 0} />
                  <span className="text-xs uppercase tracking-[0.14em] text-muted">
                    {Math.round((run.job?.progress ?? 0) * 100)}%
                  </span>
                </div>,
                formatTimestamp(run.updated_at),
              ])}
            />
          </div>
        </Panel>

        {selected ? (
          <DetailPanel
            title="Selected run"
            items={[
              { label: "Run ID", value: selected.id },
              { label: "Status", value: <StatusBadge status={selected.status} /> },
              { label: "Plan", value: selected.plan_id ?? "n/a" },
              { label: "Comparison", value: selected.comparison_id ?? "n/a" },
              { label: "Strategy", value: String(selected.summary_json.strategy ?? "n/a") },
              { label: "Scenario family", value: String(selected.summary_json.scenario_family ?? "n/a") },
              { label: "Updated", value: formatTimestamp(selected.updated_at) },
            ]}
          />
        ) : null}
      </div>
    </div>
  );
}
