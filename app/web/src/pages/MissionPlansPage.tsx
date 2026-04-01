import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useComparisons, useLibraryTemplates, usePlans, useReports, useReviews, useScenarios } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { InlineHint } from "@/components/ui/InlineHint";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RecommendationCard } from "@/components/ui/RecommendationCard";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function MissionPlansPage() {
  const { data: plansData, isLoading, error } = usePlans();
  const { data: scenariosData } = useScenarios();
  const { data: templatesData } = useLibraryTemplates();
  const { data: comparisonsData } = useComparisons();
  const { data: reviewsData } = useReviews();
  const { data: reportsData } = useReports();
  const queryClient = useQueryClient();
  const plans = plansData?.items ?? [];
  const scenarios = scenariosData?.items ?? [];
  const templates = templatesData?.items ?? [];
  const comparisons = comparisonsData?.items ?? [];
  const reviews = reviewsData?.items ?? [];
  const reports = reportsData?.items ?? [];

  const [selectedId, setSelectedId] = useState<string>("");
  const selected = useMemo(() => plans.find((plan) => plan.id === selectedId) ?? plans[0], [plans, selectedId]);
  const [form, setForm] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!selected) {
      setForm({
        name: "",
        scenarioId: scenarios[0]?.id ?? "",
        templateId: "",
        approvalState: "draft",
        strategy: "information_gain",
        numDrones: "4",
        reserveThreshold: "28",
        coordinationMode: "centralized",
        notes: "",
      });
      return;
    }
    setForm({
      name: selected.name,
      scenarioId: selected.scenario_id ?? "",
      templateId: selected.template_id ?? "",
      approvalState: String(selected.approval_state),
      strategy: String(selected.summary_json.strategy ?? "information_gain"),
      numDrones: String(selected.summary_json.num_drones ?? 4),
      reserveThreshold: String(selected.summary_json.return_threshold ?? selected.summary_json.return_to_base_threshold ?? 28),
      coordinationMode: String(selected.summary_json.coordination_mode ?? "centralized"),
      notes: selected.operator_notes ?? "",
    });
  }, [selected, scenarios]);

  const savePlan = useMutation({
    mutationFn: async () => {
      const payload = {
        name: form.name,
        scenario_id: form.scenarioId || undefined,
        template_id: form.templateId || undefined,
        approval_state: form.approvalState,
        strategy: form.strategy,
        num_drones: Number(form.numDrones),
        reserve_policy: { return_threshold: Number(form.reserveThreshold) },
        communication_assumptions: { coordination_mode: form.coordinationMode },
        operator_notes: form.notes,
      };
      return selected ? api.updatePlan(selected.id, payload) : api.createPlan(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["plans"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  if (isLoading) return <LoadingState label="Loading mission plans..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  const linkedComparisons = comparisons.filter((comparison) => comparison.plan_id === selected?.id);
  const linkedReviews = reviews.filter((review) => review.plan_id === selected?.id);
  const linkedReports = reports.filter((report) => report.owner_type === "plan" && report.owner_id === selected?.id);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Planning workspace"
        title="Saved missions"
        description="Mission plans remain the reusable handoff object for comparison, launch, monitoring, review, and reporting. The guided intake now feeds directly into this workspace."
        actions={
          <>
            <Link to="/mission-intake" className="secondary-button">
              Start new mission
            </Link>
            <button type="button" onClick={() => savePlan.mutate()} className="primary-button">
              {selected ? "Update mission plan" : "Create mission plan"}
            </button>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Mission plans" value={plans.length} />
        <MetricCard label="Approval state" value={selected?.approval_state ?? "draft"} emphasis="accent" />
        <MetricCard label="Linked runs" value={selected?.linked_run_ids_json.length ?? 0} />
        <MetricCard label="Linked reviews" value={linkedReviews.length} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <Panel
          eyebrow="Library"
          title="Saved mission plans"
          description="Select an existing mission plan to inspect its context, linked workflow objects, and current recommendation snapshot."
        >
          {plans.length === 0 ? (
            <EmptyState
              title="No mission plans yet"
              body="Create a mission plan from a scenario or doctrine template to make the rest of the workflow coherent."
            />
          ) : (
            <DataTable
              columns={["Plan", "Approval", "Strategy", "Runs"]}
              rows={plans.map((plan) => [
                <button
                  type="button"
                  onClick={() => setSelectedId(plan.id)}
                  className="text-left font-medium hover:text-accentStrong"
                >
                  {plan.name}
                </button>,
                <StatusBadge status={plan.approval_state} />,
                String(plan.summary_json.strategy ?? "n/a"),
                plan.linked_run_ids_json.length,
              ])}
            />
          )}
        </Panel>

        <div className="space-y-6">
          <Panel
            eyebrow="Workspace"
            title={selected ? selected.name : "Create mission plan"}
            description="Primary action: validate the scenario link, strategy, reserve policy, and notes before comparing or launching."
            actions={selected ? <StatusBadge status={selected.approval_state} /> : undefined}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <label>
                <span className="field-label">Plan name</span>
                <input className="field-input" value={form.name ?? ""} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
              </label>
              <label>
                <span className="field-label">Approval state</span>
                <select className="field-input" value={form.approvalState ?? "draft"} onChange={(event) => setForm((current) => ({ ...current, approvalState: event.target.value }))}>
                  {["draft", "recommended", "approved", "archived"].map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="field-label">Linked scenario</span>
                <select className="field-input" value={form.scenarioId ?? ""} onChange={(event) => setForm((current) => ({ ...current, scenarioId: event.target.value }))}>
                  <option value="">None</option>
                  {scenarios.map((scenario) => (
                    <option key={scenario.id} value={scenario.id}>
                      {scenario.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="field-label">Template</span>
                <select className="field-input" value={form.templateId ?? ""} onChange={(event) => setForm((current) => ({ ...current, templateId: event.target.value }))}>
                  <option value="">None</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span className="field-label">Strategy</span>
                <input className="field-input" value={form.strategy ?? ""} onChange={(event) => setForm((current) => ({ ...current, strategy: event.target.value }))} />
              </label>
              <label>
                <span className="field-label">Drone count</span>
                <input className="field-input" value={form.numDrones ?? ""} onChange={(event) => setForm((current) => ({ ...current, numDrones: event.target.value }))} />
              </label>
              <label>
                <span className="field-label">Reserve threshold</span>
                <input className="field-input" value={form.reserveThreshold ?? ""} onChange={(event) => setForm((current) => ({ ...current, reserveThreshold: event.target.value }))} />
              </label>
              <label>
                <span className="field-label">Coordination mode</span>
                <select className="field-input" value={form.coordinationMode ?? "centralized"} onChange={(event) => setForm((current) => ({ ...current, coordinationMode: event.target.value }))}>
                  <option value="centralized">centralized</option>
                  <option value="decentralized">decentralized</option>
                </select>
              </label>
            </div>
            <label className="mt-4 block">
              <span className="field-label">Operator notes</span>
              <textarea className="field-textarea" value={form.notes ?? ""} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
            </label>
            <InlineHint>
              Use notes for assumptions, operator intent, and briefings. They become more valuable once the plan is linked to comparisons, runs, and reviews.
            </InlineHint>
          </Panel>

          {selected ? (
            <div className="grid gap-6 xl:grid-cols-[1fr_0.92fr]">
              <RecommendationCard
                strategy={selected.recommendation_json?.recommended_strategy as string | null | undefined}
                searchPattern={selected.recommendation_json?.recommended_search_pattern as string | null | undefined}
                searchPatternLabel={selected.recommendation_json?.recommended_search_pattern_label as string | null | undefined}
                searchPatternSummary={selected.recommendation_json?.search_pattern_summary as string | null | undefined}
                searchPatternReason={selected.recommendation_json?.search_pattern_reason as string | null | undefined}
                searchPatternFitSummary={selected.recommendation_json?.search_pattern_fit_summary as string | null | undefined}
                drones={selected.recommendation_json?.recommended_drone_count as number | null | undefined}
                reserveThreshold={selected.recommendation_json?.recommended_return_threshold as number | null | undefined}
                explanation={String(selected.recommendation_json?.explanation ?? "Recommendation snapshot stored with the plan.")}
                conciseSummary={String(selected.recommendation_json?.concise_summary ?? selected.recommendation_json?.explanation ?? "Recommendation snapshot stored with the plan.")}
                topAlternativeSummary={selected.recommendation_json?.top_alternative_summary as string | null | undefined}
                keyTradeoffs={(selected.recommendation_json?.key_tradeoffs as string[] | undefined) ?? []}
                keyRisks={(selected.recommendation_json?.key_risks as string[] | undefined) ?? []}
                teamCoordinationLabel={selected.recommendation_json?.team_coordination_label as string | null | undefined}
                assetPackage={selected.asset_package ?? undefined}
                riskSummary={selected.recommendation_json?.risk_summary as Record<string, unknown> | undefined}
                uncertaintySummary={selected.recommendation_json?.uncertainty_summary as Record<string, unknown> | undefined}
                technicalDetails={selected.recommendation_json?.technical_details as Record<string, unknown> | undefined}
              />
              <DetailPanel
                title="Linked workflow"
                items={[
                  { label: "Latest comparison", value: selected.latest_comparison_id ?? "n/a" },
                  { label: "Latest review", value: selected.latest_review_id ?? "n/a" },
                  { label: "Runs", value: selected.linked_run_ids_json.length ? selected.linked_run_ids_json.join(", ") : "n/a" },
                  { label: "Reports", value: linkedReports.length ? String(linkedReports.length) : "n/a" },
                  {
                    label: "Fleet package",
                    value:
                      selected.asset_package?.operator_summary ??
                      String((selected.summary_json.asset_package as Record<string, unknown> | undefined)?.operator_summary ?? "n/a"),
                  },
                ]}
              />
            </div>
          ) : null}

          {selected ? (
            <Panel
              eyebrow="Next actions"
              title="Continue the workflow"
              description="Mission plans should move naturally into comparison, recommendation, launch, and review."
            >
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Link to="/comparisons" className="secondary-button">
                  Compare plan
                </Link>
                <Link to="/recommendations" className="secondary-button">
                  Brief recommendation
                </Link>
                <Link to="/mission-control" className="secondary-button">
                  Launch monitored run
                </Link>
                <Link to="/reviews" className="secondary-button">
                  Open review center
                </Link>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-3">
                <MetricCard label="Comparisons" value={linkedComparisons.length} />
                <MetricCard label="Reviews" value={linkedReviews.length} />
                <MetricCard label="Reports" value={linkedReports.length} />
              </div>
            </Panel>
          ) : null}
        </div>
      </div>
    </div>
  );
}
