import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useLibraryTemplates, usePlans, useScenarios } from "@/api/hooks";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function MissionPlansPage() {
  const { data: plansData, isLoading, error } = usePlans();
  const { data: scenariosData } = useScenarios();
  const { data: templatesData } = useLibraryTemplates();
  const queryClient = useQueryClient();
  const plans = plansData?.items ?? [];
  const scenarios = scenariosData?.items ?? [];
  const templates = templatesData?.items ?? [];
  const [selectedId, setSelectedId] = useState<string>("");
  const selected = useMemo(() => plans.find((plan) => plan.id === selectedId), [plans, selectedId]);
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
      reserveThreshold: String(selected.summary_json.return_to_base_threshold ?? 28),
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
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["plans"] }),
  });

  if (isLoading) return <LoadingState label="Loading mission plans..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  return (
    <div className="grid gap-6 xl:grid-cols-[1.05fr_1fr]">
      <Panel title="Mission Plans" description="The central operator-facing object for planning, comparison, launch, and review.">
        {plans.length === 0 ? (
          <EmptyState title="No mission plans yet" body="Create a plan from a scenario or doctrine template." />
        ) : (
          <DataTable
            columns={["Plan", "Approval", "Strategy", "Runs"]}
            rows={plans.map((plan) => [
              <button type="button" onClick={() => setSelectedId(plan.id)} className="text-left font-medium hover:text-accent">
                {plan.name}
              </button>,
              <StatusBadge status={plan.approval_state} />,
              String(plan.summary_json.strategy ?? "n/a"),
              plan.linked_run_ids_json.length,
            ])}
          />
        )}
      </Panel>
      <Panel title={selected ? "Review Or Edit Plan" : "Create Mission Plan"} description="Capture plan assumptions, strategy, reserve policy, and linked scenario context.">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2 text-sm text-muted">
            <span>Plan name</span>
            <input className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.name ?? ""} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
          </label>
          <label className="space-y-2 text-sm text-muted">
            <span>Approval state</span>
            <select className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.approvalState ?? "draft"} onChange={(event) => setForm((current) => ({ ...current, approvalState: event.target.value }))}>
              {["draft", "recommended", "approved", "archived"].map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label className="space-y-2 text-sm text-muted">
            <span>Scenario</span>
            <select className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.scenarioId ?? ""} onChange={(event) => setForm((current) => ({ ...current, scenarioId: event.target.value }))}>
              <option value="">None</option>
              {scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}
            </select>
          </label>
          <label className="space-y-2 text-sm text-muted">
            <span>Template</span>
            <select className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.templateId ?? ""} onChange={(event) => setForm((current) => ({ ...current, templateId: event.target.value }))}>
              <option value="">None</option>
              {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
            </select>
          </label>
          <label className="space-y-2 text-sm text-muted">
            <span>Strategy</span>
            <input className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.strategy ?? ""} onChange={(event) => setForm((current) => ({ ...current, strategy: event.target.value }))} />
          </label>
          <label className="space-y-2 text-sm text-muted">
            <span>Drone count</span>
            <input className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.numDrones ?? ""} onChange={(event) => setForm((current) => ({ ...current, numDrones: event.target.value }))} />
          </label>
          <label className="space-y-2 text-sm text-muted">
            <span>Reserve threshold</span>
            <input className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.reserveThreshold ?? ""} onChange={(event) => setForm((current) => ({ ...current, reserveThreshold: event.target.value }))} />
          </label>
          <label className="space-y-2 text-sm text-muted">
            <span>Coordination mode</span>
            <select className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.coordinationMode ?? "centralized"} onChange={(event) => setForm((current) => ({ ...current, coordinationMode: event.target.value }))}>
              <option value="centralized">centralized</option>
              <option value="decentralized">decentralized</option>
            </select>
          </label>
        </div>
        <label className="mt-4 block space-y-2 text-sm text-muted">
          <span>Operator notes</span>
          <textarea className="min-h-32 w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form.notes ?? ""} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} />
        </label>
        <button type="button" onClick={() => savePlan.mutate()} className="mt-5 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300">
          {selected ? "Update Mission Plan" : "Create Mission Plan"}
        </button>
        {selected && (
          <pre className="mt-5 overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
            {JSON.stringify(selected.recommendation_json, null, 2)}
          </pre>
        )}
      </Panel>
    </div>
  );
}
