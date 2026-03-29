import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useComparisons, usePlans } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

const strategyOptions = [
  "random_sweep",
  "sector_search",
  "probability_greedy",
  "auction_based",
  "information_gain",
];

export function PlanComparisonPage() {
  const { data: comparisonsData, isLoading, error } = useComparisons();
  const { data: plansData } = usePlans();
  const queryClient = useQueryClient();
  const comparisons = comparisonsData?.items ?? [];
  const plans = plansData?.items ?? [];
  const [selectedId, setSelectedId] = useState<string>("");
  const [form, setForm] = useState({
    name: "",
    planId: "",
    strategies: strategyOptions.join(", "),
    droneCounts: "3, 4, 5",
    coordinationModes: "centralized, decentralized",
    returnThresholds: "20, 28, 35",
    numSeeds: "2",
  });

  const selected = useMemo(
    () => comparisons.find((comparison) => comparison.id === selectedId) ?? comparisons[0],
    [comparisons, selectedId],
  );

  const createComparison = useMutation({
    mutationFn: () =>
      api.createComparison({
        name: form.name || undefined,
        plan_id: form.planId || undefined,
        strategies: splitCsv(form.strategies),
        drone_counts: splitCsv(form.droneCounts).map((value) => Number(value)),
        coordination_modes: splitCsv(form.coordinationModes),
        return_thresholds: splitCsv(form.returnThresholds).map((value) => Number(value)),
        num_seeds: Number(form.numSeeds) || 2,
      }),
    onSuccess: async (comparison) => {
      setSelectedId(comparison.id);
      await queryClient.invalidateQueries({ queryKey: ["comparisons"] });
    },
  });

  const launchCandidate = useMutation({
    mutationFn: ({ comparisonId, candidateId }: { comparisonId: string; candidateId: string }) =>
      api.launchComparisonRun(comparisonId, { candidate_id: candidateId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
      await queryClient.invalidateQueries({ queryKey: ["comparisons"] });
    },
  });

  if (isLoading) return <LoadingState label="Loading saved comparisons..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  const rankedCandidates = selected?.candidates ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Saved Comparisons" value={comparisons.length} />
        <MetricCard label="Ranked Candidates" value={rankedCandidates.length} />
        <MetricCard label="Top Strategy" value={String(selected?.recommendation_json?.strategy ?? "n/a")} />
        <MetricCard
          label="Confidence"
          value={`${Math.round(Number(selected?.uncertainty_json?.confidence ?? 0) * 100)}%`}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_1fr]">
        <Panel title="Comparison Workspace" description="Saved side-by-side evaluation bundles linked to mission plans.">
          {comparisons.length === 0 ? (
            <EmptyState
              title="No saved comparisons yet"
              body="Create a comparison workspace to rank strategies, drone counts, coordination modes, and reserve policies."
            />
          ) : (
            <DataTable
              columns={["Comparison", "Status", "Plan", "Updated"]}
              rows={comparisons.map((comparison) => [
                <button
                  type="button"
                  onClick={() => setSelectedId(comparison.id)}
                  className="text-left font-medium hover:text-accent"
                >
                  {comparison.name}
                </button>,
                <StatusBadge status={comparison.status} />,
                comparison.plan_id ?? "ad hoc",
                formatTimestamp(comparison.updated_at),
              ])}
            />
          )}
        </Panel>

        <Panel title="Create Or Refresh Comparison" description="Run a lightweight evaluation bundle and save the result for later launch and reporting.">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-muted">
              <span>Comparison name</span>
              <input
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              />
            </label>
            <label className="space-y-2 text-sm text-muted">
              <span>Mission plan</span>
              <select
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={form.planId}
                onChange={(event) => setForm((current) => ({ ...current, planId: event.target.value }))}
              >
                <option value="">None</option>
                {plans.map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-sm text-muted">
              <span>Strategies</span>
              <input
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={form.strategies}
                onChange={(event) => setForm((current) => ({ ...current, strategies: event.target.value }))}
              />
            </label>
            <label className="space-y-2 text-sm text-muted">
              <span>Drone counts</span>
              <input
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={form.droneCounts}
                onChange={(event) => setForm((current) => ({ ...current, droneCounts: event.target.value }))}
              />
            </label>
            <label className="space-y-2 text-sm text-muted">
              <span>Coordination modes</span>
              <input
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={form.coordinationModes}
                onChange={(event) => setForm((current) => ({ ...current, coordinationModes: event.target.value }))}
              />
            </label>
            <label className="space-y-2 text-sm text-muted">
              <span>Reserve thresholds</span>
              <input
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={form.returnThresholds}
                onChange={(event) => setForm((current) => ({ ...current, returnThresholds: event.target.value }))}
              />
            </label>
          </div>
          <label className="mt-4 block space-y-2 text-sm text-muted">
            <span>Seeds per candidate</span>
            <input
              className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
              value={form.numSeeds}
              onChange={(event) => setForm((current) => ({ ...current, numSeeds: event.target.value }))}
            />
          </label>
          <button
            type="button"
            onClick={() => createComparison.mutate()}
            className="mt-5 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300"
          >
            Save Comparison
          </button>
        </Panel>
      </div>

      {selected && (
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.9fr]">
          <Panel
            title="Ranked Candidate Plans"
            description="Ranked outputs can be launched directly into a mission run."
          >
            <DataTable
              columns={["Rank", "Candidate", "Strategy", "Success", "Time", "Action"]}
              rows={rankedCandidates.map((candidate) => [
                candidate.rank,
                candidate.name,
                String(candidate.config_json.strategy ?? "n/a"),
                String(candidate.summary_json.success_rate ?? candidate.summary_json.mission_success ?? "n/a"),
                String(candidate.summary_json.mean_time_to_detection ?? candidate.summary_json.time_to_detection ?? "n/a"),
                <button
                  type="button"
                  onClick={() =>
                    launchCandidate.mutate({
                      comparisonId: selected.id,
                      candidateId: candidate.id,
                    })
                  }
                  className="rounded-xl border border-accent/30 px-3 py-2 text-xs font-semibold text-accent hover:border-accent hover:bg-accent/10"
                >
                  Launch Run
                </button>,
              ])}
            />
          </Panel>
          <Panel title="Recommendation Summary" description="Persisted rationale, uncertainty band, and sensitivity signal.">
            <div className="space-y-4">
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
                {JSON.stringify(selected.recommendation_json, null, 2)}
              </pre>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
                {JSON.stringify(selected.uncertainty_json, null, 2)}
              </pre>
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
                {JSON.stringify(selected.sensitivity_json, null, 2)}
              </pre>
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
