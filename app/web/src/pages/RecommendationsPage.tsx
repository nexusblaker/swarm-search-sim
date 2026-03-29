import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { api } from "@/api/client";
import { usePlans } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Panel } from "@/components/ui/Panel";

export function RecommendationsPage() {
  const { data, isLoading, error } = usePlans();
  const plans = data?.items ?? [];
  const [planId, setPlanId] = useState("");
  const recommendation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.recommend(payload),
  });

  if (isLoading) return <LoadingState label="Loading mission plans..." />;
  if (error) return <ErrorState message={(error as Error).message} />;
  if (plans.length === 0) return <EmptyState title="No mission plans available" body="Create a mission plan before requesting recommendations." />;

  return (
    <div className="space-y-6">
      <Panel title="Recommendation Workspace" description="Request and inspect a recommendation snapshot for a mission plan.">
        <div className="flex flex-col gap-4 md:flex-row">
          <select className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white md:max-w-md" value={planId} onChange={(event) => setPlanId(event.target.value)}>
            <option value="">Select mission plan</option>
            {plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name}</option>)}
          </select>
          <button type="button" onClick={() => planId && recommendation.mutate({ plan_id: planId, num_seeds: 2 })} className="rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300">
            Generate Recommendation
          </button>
        </div>
      </Panel>
      {recommendation.data && (
        <>
          <div className="grid gap-6 xl:grid-cols-[1.05fr_1fr]">
            <Panel title="Top Recommendation" description={recommendation.data.explanation}>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-border bg-surfaceAlt/75 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">Strategy</p>
                  <p className="mt-2 text-lg font-semibold text-white">{recommendation.data.recommended_strategy}</p>
                </div>
                <div className="rounded-2xl border border-border bg-surfaceAlt/75 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">Drone count</p>
                  <p className="mt-2 text-lg font-semibold text-white">{recommendation.data.recommended_drone_count}</p>
                </div>
                <div className="rounded-2xl border border-border bg-surfaceAlt/75 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-muted">Reserve threshold</p>
                  <p className="mt-2 text-lg font-semibold text-white">{recommendation.data.recommended_return_threshold}</p>
                </div>
              </div>
            </Panel>
            <Panel title="Risk And Uncertainty" description="Explainable planning support outputs from the backend.">
              <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-muted">{JSON.stringify({ risk: recommendation.data.risk_summary, uncertainty: recommendation.data.uncertainty_summary }, null, 2)}</pre>
            </Panel>
          </div>
          <Panel title="Candidate Support" description="Candidate plans evaluated to support the recommendation.">
            <DataTable
              columns={["Strategy", "Drones", "Coordination", "Success", "Detection Time", "Failure Modes"]}
              rows={recommendation.data.candidate_plans.map((candidate) => [
                String(candidate.strategy ?? "n/a"),
                String(candidate.drone_count ?? "n/a"),
                String(candidate.coordination_mode ?? "n/a"),
                String(candidate.expected_success_rate ?? "n/a"),
                String(candidate.expected_detection_time ?? "n/a"),
                String((candidate.failure_modes as string[] | undefined)?.join(", ") ?? "n/a"),
              ])}
            />
          </Panel>
        </>
      )}
    </div>
  );
}
