import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useComparisons, usePlans } from "@/api/hooks";
import { ComparisonSummaryCard } from "@/components/ui/ComparisonSummaryCard";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { InlineHint } from "@/components/ui/InlineHint";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
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
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const launchCandidate = useMutation({
    mutationFn: ({ comparisonId, candidateId }: { comparisonId: string; candidateId: string }) =>
      api.launchComparisonRun(comparisonId, { candidate_id: candidateId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
      await queryClient.invalidateQueries({ queryKey: ["comparisons"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  if (isLoading) return <LoadingState label="Loading saved comparisons..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  const rankedCandidates = selected?.candidates ?? [];
  const topCandidate = rankedCandidates[0];

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Pre-mission analysis"
        title="Plan comparison"
        description="Compare candidate strategies, drone counts, coordination modes, and reserve thresholds before committing to a run. The goal is to make tradeoffs obvious, not hidden."
        actions={
          <button type="button" onClick={() => createComparison.mutate()} className="primary-button">
            Save comparison
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Saved comparisons" value={comparisons.length} />
        <MetricCard label="Ranked candidates" value={rankedCandidates.length} />
        <MetricCard
          label="Top pattern"
          value={String(selected?.recommendation_json?.search_pattern_label ?? selected?.recommendation_json?.strategy ?? "n/a")}
          emphasis="accent"
        />
        <MetricCard label="Confidence" value={`${Math.round(Number(selected?.uncertainty_json?.confidence ?? 0) * 100)}%`} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.94fr_1.06fr]">
        <Panel
          eyebrow="Setup"
          title="Define the candidate search space"
          description="Choose the mission plan to compare against, then set the strategy, drone, comms, and reserve ranges to evaluate."
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label>
              <span className="field-label">Comparison name</span>
              <input className="field-input" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
            </label>
            <label>
              <span className="field-label">Mission plan</span>
              <select className="field-input" value={form.planId} onChange={(event) => setForm((current) => ({ ...current, planId: event.target.value }))}>
                <option value="">None</option>
                {plans.map((plan) => (
                  <option key={plan.id} value={plan.id}>
                    {plan.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="field-label">Strategies</span>
              <input className="field-input" value={form.strategies} onChange={(event) => setForm((current) => ({ ...current, strategies: event.target.value }))} />
            </label>
            <label>
              <span className="field-label">Drone counts</span>
              <input className="field-input" value={form.droneCounts} onChange={(event) => setForm((current) => ({ ...current, droneCounts: event.target.value }))} />
            </label>
            <label>
              <span className="field-label">Coordination modes</span>
              <input className="field-input" value={form.coordinationModes} onChange={(event) => setForm((current) => ({ ...current, coordinationModes: event.target.value }))} />
            </label>
            <label>
              <span className="field-label">Reserve thresholds</span>
              <input className="field-input" value={form.returnThresholds} onChange={(event) => setForm((current) => ({ ...current, returnThresholds: event.target.value }))} />
            </label>
          </div>
          <label className="mt-4 block">
            <span className="field-label">Seeds per candidate</span>
            <input className="field-input" value={form.numSeeds} onChange={(event) => setForm((current) => ({ ...current, numSeeds: event.target.value }))} />
          </label>
          <InlineHint>
            Primary action: keep the candidate set tight enough that the recommendation feels explainable, not arbitrary.
          </InlineHint>
        </Panel>

        <Panel
          eyebrow="Workspace"
          title="Saved comparisons"
          description="Open a saved analysis workspace to inspect the ranked outcome and launch a run from a winning candidate."
        >
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
                  className="text-left font-medium hover:text-accentStrong"
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
      </div>

      {selected ? (
        <>
          <div className="grid gap-6 xl:grid-cols-3">
            <ComparisonSummaryCard
              title={`Top recommendation: ${String(selected.recommendation_json?.search_pattern_label ?? selected.recommendation_json?.strategy ?? "n/a")}`}
              description="This summary shows why the winning candidate surfaced to the top of the ranked set."
              metrics={[
                { label: "Top pattern", value: String(selected.recommendation_json?.search_pattern_label ?? selected.recommendation_json?.strategy ?? "n/a"), tone: "good" },
                { label: "Confidence", value: `${Math.round(Number(selected.uncertainty_json?.confidence ?? 0) * 100)}%` },
                { label: "Candidates", value: String(rankedCandidates.length) },
              ]}
            />
            <ComparisonSummaryCard
              title="Uncertainty"
              description="Use this to explain how stable the recommendation is when assumptions move."
              metrics={[
                { label: "Band", value: String(selected.uncertainty_json?.band ?? "n/a") },
                { label: "Spread", value: String(selected.uncertainty_json?.spread ?? "n/a"), tone: "warning" },
                { label: "Confidence", value: String(selected.uncertainty_json?.confidence ?? "n/a") },
              ]}
            />
            <ComparisonSummaryCard
              title="Sensitivity"
              description="Sensitivity explains which assumptions most influence the ranking."
              metrics={[
                { label: "Top driver", value: String(selected.sensitivity_json?.top_driver ?? "n/a") },
                { label: "Most stable", value: String(selected.sensitivity_json?.most_stable ?? "n/a"), tone: "good" },
                { label: "Review", value: "Use before launch" },
              ]}
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.16fr_0.94fr]">
            <Panel
              eyebrow="Ranked results"
              title="Candidate plans"
              description="The ranked table is designed to make launch decisions fast. Select the candidate that best balances mission success, speed, and operational risk."
            >
              <DataTable
                columns={["Rank", "Candidate", "Pattern", "Success", "Detection time", "Launch"]}
                rows={rankedCandidates.map((candidate) => [
                  candidate.rank,
                  candidate.name,
                  String(candidate.summary_json.search_pattern_label ?? candidate.config_json.search_pattern ?? candidate.config_json.strategy ?? "n/a"),
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
                    className="secondary-button"
                  >
                    Launch candidate
                  </button>,
                ])}
              />
            </Panel>

            <Panel
              eyebrow="Why this won"
              title={topCandidate ? topCandidate.name : "No top candidate"}
              description="This panel gives a plainer-language briefing on the current winning option."
            >
              {topCandidate ? (
                <div className="space-y-4">
                  <div className="panel-subtle p-5">
                    <p className="section-kicker">Primary tradeoff</p>
                    <p className="mt-2 text-base font-medium text-white">
                      {String(topCandidate.summary_json.search_pattern_label ?? topCandidate.config_json.search_pattern ?? topCandidate.config_json.strategy ?? "n/a")} surfaced as the best balance of expected success and search speed.
                    </p>
                    <p className="mt-3 text-sm leading-6 text-muted">
                      {String(topCandidate.summary_json.search_pattern_reason ?? "Use this candidate when you want the cleanest path from evaluation to monitored run.")}
                    </p>
                  </div>
                  <pre className="rounded-[22px] border border-border bg-surfaceAlt/60 p-4 text-xs leading-6 text-muted">
                    {JSON.stringify(selected.recommendation_json, null, 2)}
                  </pre>
                </div>
              ) : (
                <EmptyState title="No ranked candidate" body="Create or open a comparison to populate the analysis workspace." />
              )}
            </Panel>
          </div>
        </>
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
