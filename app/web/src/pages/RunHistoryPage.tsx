import { useMemo, useState } from "react";

import { useRuns } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Panel } from "@/components/ui/Panel";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

export function RunHistoryPage() {
  const { data, isLoading, error } = useRuns(5000);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const runs = data?.items ?? [];

  const filteredRuns = useMemo(
    () =>
      runs.filter((run) => {
        const matchesStatus = status === "all" || run.status === status;
        const haystack = `${run.id} ${run.plan_id ?? ""} ${run.comparison_id ?? ""} ${run.summary_json.strategy ?? ""}`.toLowerCase();
        return matchesStatus && haystack.includes(search.toLowerCase());
      }),
    [runs, search, status],
  );

  if (isLoading) return <LoadingState label="Loading run history..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  return (
    <Panel title="Run History" description="Search and filter simulated missions by source plan, status, and strategy.">
      <div className="mb-4 grid gap-3 md:grid-cols-[1fr_220px]">
        <input className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" placeholder="Search runs" value={search} onChange={(event) => setSearch(event.target.value)} />
        <select className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="all">All statuses</option>
          {Array.from(new Set(runs.map((run) => run.status))).map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </div>
      <DataTable
        columns={["Run", "Status", "Source", "Strategy", "Progress", "Updated"]}
        rows={filteredRuns.map((run) => [
          run.id,
          <StatusBadge status={run.status} />,
          run.plan_id ? `plan:${run.plan_id}` : run.comparison_id ? `comparison:${run.comparison_id}` : run.scenario_id,
              String(run.summary_json.strategy ?? "n/a"),
          <div className="min-w-40 space-y-2"><ProgressBar value={run.job?.progress ?? 0} /><span className="text-xs text-muted">{Math.round((run.job?.progress ?? 0) * 100)}%</span></div>,
          formatTimestamp(run.updated_at),
        ])}
      />
    </Panel>
  );
}
