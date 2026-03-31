import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { api } from "@/api/client";
import { usePlans } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RecommendationCard } from "@/components/ui/RecommendationCard";
import { RiskIndicator } from "@/components/ui/RiskIndicator";

export function RecommendationsPage() {
  const { data, isLoading, error } = usePlans();
  const plans = data?.items ?? [];
  const [planId, setPlanId] = useState("");
  const recommendation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.recommend(payload),
  });

  if (isLoading) return <LoadingState label="Loading mission plans..." />;
  if (error) return <ErrorState message={(error as Error).message} />;
  if (plans.length === 0) {
    return (
      <EmptyState
        title="No mission plans available"
        body="Create a mission plan before requesting recommendations."
      />
    );
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Decision support"
        title="Plan brief"
        description="Generate a short, operator-facing recommendation brief for a saved mission plan, then inspect the supporting mission options below."
        actions={
          <button
            type="button"
            onClick={() => planId && recommendation.mutate({ plan_id: planId, num_seeds: 2 })}
            className="primary-button"
          >
            Generate recommendation
          </button>
        }
      />

      <Panel
        eyebrow="Selection"
        title="Choose the mission to brief"
        description="Pick a saved mission plan, then generate the latest recommendation summary."
      >
        <div className="max-w-md">
          <label>
            <span className="field-label">Mission plan</span>
            <select className="field-input" value={planId} onChange={(event) => setPlanId(event.target.value)}>
              <option value="">Select mission plan</option>
              {plans.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      {recommendation.data ? (
        <>
          <RecommendationCard
            strategy={recommendation.data.recommended_strategy}
            drones={recommendation.data.recommended_drone_count}
            reserveThreshold={recommendation.data.recommended_return_threshold}
            explanation={recommendation.data.explanation}
            conciseSummary={recommendation.data.concise_summary}
            topAlternativeSummary={recommendation.data.top_alternative_summary}
            keyTradeoffs={recommendation.data.key_tradeoffs}
            keyRisks={recommendation.data.key_risks}
            teamCoordinationLabel={recommendation.data.team_coordination_label}
            assetPackage={recommendation.data.asset_package}
            riskSummary={recommendation.data.risk_summary}
            uncertaintySummary={recommendation.data.uncertainty_summary}
            technicalDetails={recommendation.data.technical_details}
          />

          <div className="grid gap-6 xl:grid-cols-3">
            <RiskIndicator
              label="Battery margin risk"
              value={String(recommendation.data.risk_summary?.battery_risk ?? "n/a")}
              tone="warning"
            />
            <RiskIndicator
              label="Comms fragility"
              value={String(recommendation.data.risk_summary?.communications_fragility ?? "n/a")}
              tone="warning"
            />
            <RiskIndicator
              label="Coverage overlap risk"
              value={String(recommendation.data.risk_summary?.overlap_risk ?? "n/a")}
            />
          </div>

          <Panel
            eyebrow="Mission options"
            title="Mission options behind the brief"
            description="These are the candidate options the recommendation engine evaluated before choosing the lead plan."
          >
            <DataTable
              columns={["Search style", "Drones", "Team coordination", "Success", "Detection time", "Watch items"]}
              rows={recommendation.data.candidate_plans.map((candidate) => [
                String(candidate.strategy ?? "n/a"),
                String(candidate.drone_count ?? "n/a"),
                String(candidate.team_coordination_label ?? candidate.coordination_mode ?? "n/a"),
                String(candidate.expected_success_rate ?? "n/a"),
                String(candidate.expected_detection_time ?? "n/a"),
                String((candidate.failure_modes as string[] | undefined)?.join(", ") ?? "n/a"),
              ])}
            />
          </Panel>
        </>
      ) : (
        <EmptyState
          title="No recommendation generated yet"
          body="Select a mission plan and generate a recommendation to see a briefing-ready summary here."
        />
      )}
    </div>
  );
}
