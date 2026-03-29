import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useScenarios } from "@/api/hooks";
import type { ScenarioRecord } from "@/api/types";
import { DataTable } from "@/components/ui/DataTable";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { InlineHint } from "@/components/ui/InlineHint";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { formatTimestamp } from "@/lib/format";

function buildScenarioPayload(source?: ScenarioRecord, form?: Record<string, string>) {
  const base = structuredClone((source?.config_json ?? { scenario: {} }) as Record<string, unknown>);
  const scenario = (base.scenario ?? {}) as Record<string, unknown>;
  const currentDrone = (scenario.drone ?? {}) as Record<string, unknown>;
  const currentBattery = (scenario.battery_policy ?? {}) as Record<string, unknown>;
  const currentComms = (scenario.communication ?? {}) as Record<string, unknown>;
  const currentTargetAssumptions = (scenario.target_assumptions ?? {}) as Record<string, unknown>;
  return {
    scenario: {
      ...scenario,
      name: form?.name ?? scenario.name ?? "Mission Scenario",
      map_size: [Number(form?.width ?? 18), Number(form?.height ?? 14)],
      num_drones: Number(form?.numDrones ?? scenario.num_drones ?? 4),
      strategy: form?.strategy ?? scenario.strategy ?? "information_gain",
      weather: form?.weather ?? scenario.weather ?? "clear",
      max_steps: Number(form?.maxSteps ?? scenario.max_steps ?? 40),
      scenario_family: form?.scenarioFamily ?? scenario.scenario_family ?? "mixed_terrain",
      drone: {
        ...currentDrone,
        battery: Number(form?.battery ?? currentDrone.battery ?? 120),
        sensor_range: Number(form?.sensorRange ?? currentDrone.sensor_range ?? 4),
      },
      target_assumptions: {
        ...currentTargetAssumptions,
        behavior: form?.targetBehavior ?? currentTargetAssumptions.behavior ?? "terrain_biased",
      },
      battery_policy: {
        ...currentBattery,
        return_threshold: Number(form?.returnThreshold ?? currentBattery.return_threshold ?? 28),
      },
      communication: {
        ...currentComms,
        coordination_mode: form?.coordinationMode ?? currentComms.coordination_mode ?? "centralized",
      },
    },
  };
}

export function ScenariosPage() {
  const { data, isLoading, error } = useScenarios();
  const queryClient = useQueryClient();
  const scenarios = data?.items ?? [];
  const [selectedId, setSelectedId] = useState<string>("");
  const selected = useMemo(() => scenarios.find((scenario) => scenario.id === selectedId), [scenarios, selectedId]);
  const [form, setForm] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!selected) {
      setForm({
        name: "",
        width: "18",
        height: "14",
        numDrones: "4",
        strategy: "information_gain",
        weather: "clear",
        maxSteps: "40",
        battery: "120",
        sensorRange: "4",
        returnThreshold: "28",
        coordinationMode: "centralized",
        scenarioFamily: "mixed_terrain",
        targetBehavior: "terrain_biased",
      });
      return;
    }
    const scenario = selected.config_json.scenario as Record<string, unknown>;
    setForm({
      name: String(scenario.name ?? ""),
      width: String((scenario.map_size as number[] | undefined)?.[0] ?? 18),
      height: String((scenario.map_size as number[] | undefined)?.[1] ?? 14),
      numDrones: String(scenario.num_drones ?? 4),
      strategy: String(scenario.strategy ?? "information_gain"),
      weather: String(scenario.weather ?? "clear"),
      maxSteps: String(scenario.max_steps ?? 40),
      battery: String((scenario.drone as Record<string, unknown> | undefined)?.battery ?? 120),
      sensorRange: String((scenario.drone as Record<string, unknown> | undefined)?.sensor_range ?? 4),
      returnThreshold: String((scenario.battery_policy as Record<string, unknown> | undefined)?.return_threshold ?? 28),
      coordinationMode: String((scenario.communication as Record<string, unknown> | undefined)?.coordination_mode ?? "centralized"),
      scenarioFamily: String(scenario.scenario_family ?? "mixed_terrain"),
      targetBehavior: String((scenario.target_assumptions as Record<string, unknown> | undefined)?.behavior ?? "terrain_biased"),
    });
  }, [selected]);

  const saveScenario = useMutation({
    mutationFn: async () => {
      const payload = buildScenarioPayload(selected, form);
      return selected ? api.updateScenario(selected.id, payload) : api.createScenario(payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["scenarios"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  if (isLoading) return <LoadingState label="Loading scenarios..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Planning input"
        title="Scenario editor"
        description="Define the search environment, target assumptions, drone package, and mission envelope. The editor is grouped by what operators need to understand, not by code internals."
        actions={
          <button type="button" onClick={() => saveScenario.mutate()} className="primary-button">
            {selected ? "Update scenario" : "Create scenario"}
          </button>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Saved scenarios" value={scenarios.length} />
        <MetricCard label="Family" value={form.scenarioFamily ?? "mixed_terrain"} />
        <MetricCard label="Target behavior" value={form.targetBehavior ?? "terrain_biased"} />
        <MetricCard label="Drones" value={form.numDrones ?? "4"} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel
          eyebrow="Library"
          title="Saved scenarios"
          description="Select an existing scenario to edit it or start from a blank definition with sensible defaults."
        >
          {scenarios.length === 0 ? (
            <EmptyState
              title="No scenarios found"
              body="Create your first scenario here, or open the doctrine library to start from an operational preset."
            />
          ) : (
            <DataTable
              columns={["Scenario", "Family", "Strategy", "Updated"]}
              rows={scenarios.map((scenario) => [
                <button
                  type="button"
                  onClick={() => setSelectedId(scenario.id)}
                  className="text-left font-medium hover:text-accentStrong"
                >
                  {scenario.name}
                </button>,
                String(scenario.summary_json.scenario_family ?? "n/a"),
                String(scenario.summary_json.strategy ?? "n/a"),
                formatTimestamp(scenario.updated_at),
              ])}
            />
          )}
        </Panel>

        <div className="space-y-6">
          <Panel
            eyebrow="Overview"
            title={selected ? "Editing scenario" : "Create a new scenario"}
            description="Primary action: confirm the map, target, drone, communication, and reserve assumptions before saving."
          >
            <div className="grid gap-4 md:grid-cols-2">
              <label>
                <span className="field-label">Scenario name</span>
                <input className="field-input" value={form.name ?? ""} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
              </label>
              <label>
                <span className="field-label">Scenario family</span>
                <select className="field-input" value={form.scenarioFamily ?? "mixed_terrain"} onChange={(event) => setForm((current) => ({ ...current, scenarioFamily: event.target.value }))}>
                  {["open_terrain", "dense_forest", "mixed_terrain", "obstacle_heavy", "poor_comms", "high_wind", "low_battery_budget"].map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <InlineHint>
              Choose a family first. It gives reviewers immediate context for what kind of mission environment this scenario represents.
            </InlineHint>
          </Panel>

          <Panel eyebrow="Core settings" title="Map, target, drones, and comms" description="These are the fields most operators adjust first.">
            <div className="grid gap-4 md:grid-cols-2">
              {[
                ["width", "Map width"],
                ["height", "Map height"],
                ["numDrones", "Drone count"],
                ["strategy", "Strategy"],
                ["weather", "Weather"],
                ["targetBehavior", "Target behavior"],
                ["battery", "Battery"],
                ["sensorRange", "Sensor range"],
                ["returnThreshold", "Reserve threshold"],
                ["coordinationMode", "Coordination mode"],
                ["maxSteps", "Max steps"],
              ].map(([key, label]) => (
                <label key={key}>
                  <span className="field-label">{label}</span>
                  <input className="field-input" value={form[key] ?? ""} onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))} />
                </label>
              ))}
            </div>
          </Panel>

          <details className="panel-surface p-6">
            <summary className="cursor-pointer list-none">
              <p className="section-kicker">Advanced settings</p>
              <h3 className="mt-1 text-xl font-semibold text-white">Planner, belief, and rendering guidance</h3>
              <p className="mt-2 text-sm leading-6 text-muted">
                This section is collapsed by default so new users are not forced into low-value detail too early.
              </p>
            </summary>
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <DetailPanel
                title="What this editor configures"
                items={[
                  { label: "Map and terrain", value: "Family, width, height, and weather establish the operating picture." },
                  { label: "Target behavior", value: "The target behavior affects belief propagation and replay dynamics." },
                  { label: "Battery and return policy", value: "Reserve threshold influences when drones stop searching and route home." },
                  { label: "Communication and sensing", value: "Coordination mode and sensor range shape what drones can know and detect." },
                ]}
              />
              <DetailPanel
                title="Suggested next step"
                items={[
                  {
                    label: "If this is for planning",
                    value: "Save the scenario, then create a mission plan on top of it so recommendations and comparisons stay linked.",
                  },
                  {
                    label: "If this is for a demo",
                    value: "Keep defaults tight and use a doctrine template if you want a faster narrative path through the product.",
                  },
                ]}
              />
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
