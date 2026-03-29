import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useExperiments } from "@/api/hooks";
import type { ExperimentRecord } from "@/api/types";
import { ArtifactLink } from "@/components/ui/ArtifactLink";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Panel } from "@/components/ui/Panel";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

export function ExperimentsPage() {
  const { data, isLoading, error } = useExperiments();
  const experiments = data?.items ?? [];
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState({
    strategies: "information_gain, auction_based, probability_greedy",
    scenarioFamilies: "open_terrain, dense_forest, obstacle_heavy",
    targetBehaviors: "terrain_biased, injured_slow",
    coordinationModes: "centralized, decentralized",
    droneCounts: "3, 4",
    benchmarkSeeds: "4",
    experimentSeeds: "1",
  });

  const selected = useMemo<ExperimentRecord | undefined>(
    () => experiments.find((item) => item.id === selectedId) ?? experiments[0],
    [experiments, selectedId],
  );

  const summaryQuery = useQuery({
    queryKey: ["experiment-summary", selected?.id],
    queryFn: () => api.experimentSummary(selected!.id),
    enabled: Boolean(selected?.id),
  });

  const createExperiment = useMutation({
    mutationFn: () =>
      api.createExperiment({
        strategies: splitCsv(form.strategies),
        scenario_families: splitCsv(form.scenarioFamilies),
        target_behaviors: splitCsv(form.targetBehaviors),
        coordination_modes: splitCsv(form.coordinationModes),
        drone_counts: splitCsv(form.droneCounts).map((item) => Number(item)),
        benchmark_num_seeds: Number(form.benchmarkSeeds) || 4,
        experiment_num_seeds: Number(form.experimentSeeds) || 1,
      }),
  });

  if (isLoading) return <LoadingState label="Loading experiment browser..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  const summaryRows = normalizeExperimentSummary(summaryQuery.data?.summary);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.2fr]">
        <Panel title="Launch Experiment Batch" description="Grouped robustness experiments across strategies, scenario families, and target behaviors.">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ["Strategies", "strategies"],
              ["Scenario families", "scenarioFamilies"],
              ["Target behaviors", "targetBehaviors"],
              ["Coordination modes", "coordinationModes"],
              ["Drone counts", "droneCounts"],
            ].map(([label, key]) => (
              <label key={key} className="space-y-2 text-sm text-muted">
                <span>{label}</span>
                <input
                  className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                  value={form[key as keyof typeof form]}
                  onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))}
                />
              </label>
            ))}
            <label className="space-y-2 text-sm text-muted">
              <span>Benchmark seeds</span>
              <input
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={form.benchmarkSeeds}
                onChange={(event) => setForm((current) => ({ ...current, benchmarkSeeds: event.target.value }))}
              />
            </label>
            <label className="space-y-2 text-sm text-muted">
              <span>Experiment seeds</span>
              <input
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={form.experimentSeeds}
                onChange={(event) => setForm((current) => ({ ...current, experimentSeeds: event.target.value }))}
              />
            </label>
          </div>
          <button
            type="button"
            onClick={() => createExperiment.mutate()}
            className="mt-5 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300"
          >
            Launch Experiment
          </button>
        </Panel>

        <Panel title="Experiment History" description="Tracked experiment jobs, statuses, and artifact bundles.">
          {experiments.length === 0 ? (
            <EmptyState title="No experiments yet" body="Launch a grouped experiment batch to build comparative evidence." />
          ) : (
            <DataTable
              columns={["Experiment", "Status", "Progress", "Updated"]}
              rows={experiments.map((experiment) => [
                <button
                  type="button"
                  onClick={() => setSelectedId(experiment.id)}
                  className="text-left font-medium hover:text-accent"
                >
                  {experiment.id}
                </button>,
                <StatusBadge status={experiment.status} />,
                <div className="w-32">
                  <ProgressBar value={Math.round((experiment.job?.progress ?? 0) * 100)} />
                </div>,
                formatTimestamp(experiment.updated_at),
              ])}
            />
          )}
        </Panel>
      </div>

      {selected && (
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.95fr]">
          <Panel title="Summary Table" description="Aggregated experiment outputs from the stored summary artifact.">
            {summaryRows.length === 0 ? (
              <EmptyState title="No summary yet" body="This experiment may still be queued or the summary artifact is empty." />
            ) : (
              <DataTable
                columns={["Strategy", "Family", "Success", "Detection Time", "Overlap"]}
                rows={summaryRows.map((row) => [
                  String(row.strategy ?? "n/a"),
                  String(row.scenario_family ?? row.family ?? "n/a"),
                  String(row.success_rate ?? row.mission_success ?? "n/a"),
                  String(row.time_to_detection ?? row.mean_time_to_detection ?? "n/a"),
                  String(row.overlap_ratio ?? row.average_overlap ?? "n/a"),
                ])}
              />
            )}
          </Panel>

          <Panel title="Comparison Plot" description="Quick view of success-rate differences across strategies.">
            {summaryRows.length === 0 ? (
              <EmptyState title="No chart data yet" body="A completed experiment summary is needed to render the chart." />
            ) : (
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={summaryRows.slice(0, 8)}>
                    <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
                    <XAxis dataKey="strategy" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                    <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="success_rate" fill="#38bdf8" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
            <div className="mt-4 flex flex-wrap gap-3">
              {Object.entries(selected.artifact_paths ?? {}).map(([name, path]) => (
                <ArtifactLink
                  key={name}
                  href={`${api.baseUrl}/artifacts/experiment/${selected.id}/${name}`}
                  label={name}
                />
              ))}
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}

function splitCsv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeExperimentSummary(value: unknown): Array<Record<string, unknown>> {
  if (Array.isArray(value)) {
    return value as Array<Record<string, unknown>>;
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (Array.isArray(record.summary)) {
      return record.summary as Array<Record<string, unknown>>;
    }
  }
  return [];
}
