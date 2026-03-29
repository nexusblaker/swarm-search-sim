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
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
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
    <div className="page-stack">
      <PageHeader
        eyebrow="Analyst workspace"
        title="Experiments"
        description="Launch grouped robustness experiments, then browse the summary outputs and plots in a calmer, more presentation-ready layout."
        actions={
          <button type="button" onClick={() => createExperiment.mutate()} className="primary-button">
            Launch experiment
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Experiments" value={experiments.length} />
        <MetricCard label="Selected status" value={selected?.status ?? "n/a"} emphasis="accent" />
        <MetricCard label="Summary rows" value={summaryRows.length} />
        <MetricCard label="Artifacts" value={Object.keys(selected?.artifact_paths ?? {}).length} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.94fr_1.06fr]">
        <Panel
          eyebrow="Launch"
          title="Experiment setup"
          description="Use this form to define the parameter sweep. Keep it focused enough that the results remain easy to explain."
        >
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ["Strategies", "strategies"],
              ["Scenario families", "scenarioFamilies"],
              ["Target behaviors", "targetBehaviors"],
              ["Coordination modes", "coordinationModes"],
              ["Drone counts", "droneCounts"],
            ].map(([label, key]) => (
              <label key={key}>
                <span className="field-label">{label}</span>
                <input
                  className="field-input"
                  value={form[key as keyof typeof form]}
                  onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))}
                />
              </label>
            ))}
            <label>
              <span className="field-label">Benchmark seeds</span>
              <input className="field-input" value={form.benchmarkSeeds} onChange={(event) => setForm((current) => ({ ...current, benchmarkSeeds: event.target.value }))} />
            </label>
            <label>
              <span className="field-label">Experiment seeds</span>
              <input className="field-input" value={form.experimentSeeds} onChange={(event) => setForm((current) => ({ ...current, experimentSeeds: event.target.value }))} />
            </label>
          </div>
        </Panel>

        <Panel
          eyebrow="History"
          title="Experiment runs"
          description="Select an experiment to open its summary table, plots, and artifacts."
        >
          {experiments.length === 0 ? (
            <EmptyState title="No experiments yet" body="Launch a grouped experiment batch to build comparative evidence." />
          ) : (
            <DataTable
              columns={["Experiment", "Status", "Progress", "Updated"]}
              rows={experiments.map((experiment) => [
                <button type="button" onClick={() => setSelectedId(experiment.id)} className="text-left font-medium hover:text-accentStrong">
                  {experiment.id}
                </button>,
                <StatusBadge status={experiment.status} />,
                <div className="w-32">
                  <ProgressBar value={experiment.job?.progress ?? 0} />
                </div>,
                formatTimestamp(experiment.updated_at),
              ])}
            />
          )}
        </Panel>
      </div>

      {selected ? (
        <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
          <Panel
            eyebrow="Summary"
            title="Experiment outputs"
            description="Lead with the summary table so the experiment is understandable before diving into raw artifacts."
          >
            {summaryRows.length === 0 ? (
              <EmptyState title="No summary yet" body="This experiment may still be queued or the summary artifact is empty." />
            ) : (
              <DataTable
                columns={["Strategy", "Family", "Success", "Detection time", "Overlap"]}
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

          <div className="space-y-6">
            <Panel
              eyebrow="Plot"
              title="Success-rate comparison"
              description="A compact visual for the current selected experiment."
            >
              {summaryRows.length === 0 ? (
                <EmptyState title="No chart data yet" body="A completed experiment summary is needed to render the chart." />
              ) : (
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={summaryRows.slice(0, 8)}>
                      <CartesianGrid stroke="rgba(152,160,171,0.12)" vertical={false} />
                      <XAxis dataKey="strategy" tick={{ fill: "#98a0ab", fontSize: 12 }} />
                      <YAxis tick={{ fill: "#98a0ab", fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="success_rate" fill="#8fb4d6" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Panel>

            <Panel
              eyebrow="Artifacts"
              title="Experiment files"
              description="Open the stored plots, CSVs, and other generated experiment outputs."
            >
              <div className="flex flex-wrap gap-3">
                {Object.entries(selected.artifact_paths ?? {}).map(([name]) => (
                  <ArtifactLink
                    key={name}
                    href={`${api.baseUrl}/artifacts/experiment/${selected.id}/${name}`}
                    label={name}
                  />
                ))}
              </div>
            </Panel>
          </div>
        </div>
      ) : null}
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
