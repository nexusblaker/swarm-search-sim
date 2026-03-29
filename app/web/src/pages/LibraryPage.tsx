import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useLibraryTemplates } from "@/api/hooks";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { RiskIndicator } from "@/components/ui/RiskIndicator";

export function LibraryPage() {
  const { data, isLoading, error } = useLibraryTemplates();
  const queryClient = useQueryClient();
  const templates = data?.items ?? [];
  const [familyFilter, setFamilyFilter] = useState("all");
  const [tagFilter, setTagFilter] = useState("all");
  const filtered = useMemo(
    () =>
      templates.filter(
        (item) =>
          (familyFilter === "all" || item.family === familyFilter) &&
          (tagFilter === "all" || item.tags_json.includes(tagFilter)),
      ),
    [familyFilter, tagFilter, templates],
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
  if (templates.length === 0) {
    return (
      <EmptyState
        title="No doctrine entries found"
        body="The doctrine library will appear here once templates are available."
      />
    );
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operational presets"
        title="Doctrine library"
        description="Browse reusable mission patterns with intended use, assumptions, risks, and recommended strategies. This is the fastest path to a good demo and a clean planning workflow."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Doctrine entries" value={templates.length} />
        <MetricCard label="Families" value={new Set(templates.map((item) => item.family)).size} />
        <MetricCard label="Visible entries" value={filtered.length} />
        <MetricCard label="Recommended focus" value="Template → Plan" emphasis="accent" />
      </div>

      <Panel
        eyebrow="Filters"
        title="Find the right starting point"
        description="Use family and tags to narrow the library to the doctrine pattern that best matches the mission you want to simulate."
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label>
            <span className="field-label">Family</span>
            <select className="field-input" value={familyFilter} onChange={(event) => setFamilyFilter(event.target.value)}>
              <option value="all">All families</option>
              {Array.from(new Set(templates.map((item) => item.family))).map((family) => (
                <option key={family} value={family}>
                  {family}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Tag</span>
            <select className="field-input" value={tagFilter} onChange={(event) => setTagFilter(event.target.value)}>
              <option value="all">All tags</option>
              {Array.from(new Set(templates.flatMap((item) => item.tags_json))).map((tag) => (
                <option key={tag} value={tag}>
                  {tag}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        {filtered.map((template) => (
          <Panel
            key={template.id}
            eyebrow={template.doctrine_type}
            title={template.name}
            description={template.description}
            actions={<span className="pill">{template.family}</span>}
            footer={
              <div className="flex flex-wrap gap-3">
                <button type="button" onClick={() => createScenario.mutate(template.id)} className="secondary-button">
                  Create scenario
                </button>
                <button type="button" onClick={() => createPlan.mutate(template.id)} className="primary-button">
                  Create mission plan
                </button>
              </div>
            }
          >
            <p className="text-sm leading-7 text-white">{template.intended_use}</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <RiskIndicator
                label="Recommended strategies"
                value={template.recommended_strategies_json.join(", ")}
                tone="good"
              />
              <RiskIndicator label="Tags" value={template.tags_json.join(", ")} />
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-[22px] border border-border bg-surfaceAlt/55 p-4">
                <p className="section-kicker">Risks</p>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-muted">
                  {template.risks_json.map((risk) => (
                    <li key={risk}>• {risk}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-[22px] border border-border bg-surfaceAlt/55 p-4">
                <p className="section-kicker">Assumptions</p>
                <ul className="mt-3 space-y-2 text-sm leading-6 text-muted">
                  {template.assumptions_json.map((assumption) => (
                    <li key={assumption}>• {assumption}</li>
                  ))}
                </ul>
              </div>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
