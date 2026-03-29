import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useLibraryTemplates } from "@/api/hooks";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Panel } from "@/components/ui/Panel";

export function LibraryPage() {
  const { data, isLoading, error } = useLibraryTemplates();
  const queryClient = useQueryClient();
  const templates = data?.items ?? [];
  const [familyFilter, setFamilyFilter] = useState("all");
  const filtered = useMemo(
    () => templates.filter((item) => familyFilter === "all" || item.family === familyFilter),
    [familyFilter, templates],
  );
  const createScenario = useMutation({
    mutationFn: async (templateId: string) => {
      const template = templates.find((item) => item.id === templateId);
      return api.createScenario(template?.config_json ?? {});
    },
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["scenarios"] }),
  });
  const createPlan = useMutation({
    mutationFn: (templateId: string) => api.createPlan({ name: "Mission Plan", template_id: templateId }),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["plans"] }),
  });

  if (isLoading) return <LoadingState label="Loading doctrine library..." />;
  if (error) return <ErrorState message={(error as Error).message} />;
  if (templates.length === 0) return <EmptyState title="No doctrine entries found" body="The doctrine library will appear here once templates are available." />;

  return (
    <Panel title="Doctrine / Template Library" description="Operational presets with intended use, assumptions, risks, and strategy guidance.">
      <div className="mb-4 max-w-sm">
        <select className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={familyFilter} onChange={(event) => setFamilyFilter(event.target.value)}>
          <option value="all">All families</option>
          {Array.from(new Set(templates.map((item) => item.family))).map((family) => <option key={family} value={family}>{family}</option>)}
        </select>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        {filtered.map((template) => (
          <div key={template.id} className="rounded-3xl border border-border bg-surfaceAlt/75 p-5">
            <p className="text-xs uppercase tracking-[0.2em] text-accent">{template.doctrine_type}</p>
            <div className="mt-2 flex items-start justify-between gap-4">
              <div>
                <h3 className="text-xl font-semibold text-white">{template.name}</h3>
                <p className="mt-2 text-sm text-muted">{template.description}</p>
              </div>
              <span className="rounded-full border border-border px-3 py-1 text-xs uppercase tracking-[0.18em] text-muted">{template.family}</span>
            </div>
            <p className="mt-4 text-sm text-white">{template.intended_use}</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted">Recommended strategies</p>
                <p className="mt-2 text-sm text-white">{template.recommended_strategies_json.join(", ")}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted">Tags</p>
                <p className="mt-2 text-sm text-white">{template.tags_json.join(", ")}</p>
              </div>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted">Risks</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
                  {template.risks_json.map((risk) => <li key={risk}>{risk}</li>)}
                </ul>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-muted">Assumptions</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
                  {template.assumptions_json.map((assumption) => <li key={assumption}>{assumption}</li>)}
                </ul>
              </div>
            </div>
            <div className="mt-5 flex gap-3">
              <button type="button" onClick={() => createScenario.mutate(template.id)} className="rounded-2xl border border-border px-4 py-2 text-sm text-white hover:border-accent/40 hover:text-accent">
                Create Scenario
              </button>
              <button type="button" onClick={() => createPlan.mutate(template.id)} className="rounded-2xl bg-accent px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-sky-300">
                Create Mission Plan
              </button>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
