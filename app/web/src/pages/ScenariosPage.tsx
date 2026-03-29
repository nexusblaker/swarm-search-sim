import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useScenarios } from "@/api/hooks";
import type { ScenarioRecord } from "@/api/types";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Panel } from "@/components/ui/Panel";
import { formatTimestamp } from "@/lib/format";

function buildScenarioPayload(source?: ScenarioRecord, form?: Record<string, string>) {
  const base = structuredClone((source?.config_json ?? { scenario: {} }) as Record<string, unknown>);
  const scenario = (base.scenario ?? {}) as Record<string, unknown>;
  const currentDrone = (scenario.drone ?? {}) as Record<string, unknown>;
  const currentBattery = (scenario.battery_policy ?? {}) as Record<string, unknown>;
  const currentComms = (scenario.communication ?? {}) as Record<string, unknown>;
  return {
    scenario: {
      ...scenario,
      name: form?.name ?? scenario.name ?? "Mission Scenario",
      map_size: [Number(form?.width ?? 18), Number(form?.height ?? 14)],
      num_drones: Number(form?.numDrones ?? scenario.num_drones ?? 4),
      strategy: form?.strategy ?? scenario.strategy ?? "information_gain",
      weather: form?.weather ?? scenario.weather ?? "clear",
      max_steps: Number(form?.maxSteps ?? scenario.max_steps ?? 40),
      drone: {
        ...currentDrone,
        battery: Number(form?.battery ?? currentDrone.battery ?? 120),
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
        returnThreshold: "28",
        coordinationMode: "centralized",
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
      returnThreshold: String((scenario.battery_policy as Record<string, unknown> | undefined)?.return_threshold ?? 28),
      coordinationMode: String((scenario.communication as Record<string, unknown> | undefined)?.coordination_mode ?? "centralized"),
    });
  }, [selected]);

  const saveScenario = useMutation({
    mutationFn: async () => {
      const payload = buildScenarioPayload(selected, form);
      return selected ? api.updateScenario(selected.id, payload) : api.createScenario(payload);
    },
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["scenarios"] }),
  });

  if (isLoading) return <LoadingState label="Loading scenarios..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr]">
      <Panel title="Saved Scenarios" description="Browse and reopen scenario definitions.">
        {scenarios.length === 0 ? (
          <EmptyState title="No scenarios found" body="Create a scenario from the editor on the right." />
        ) : (
          <DataTable
            columns={["Scenario", "Family", "Strategy", "Updated"]}
            rows={scenarios.map((scenario) => [
              <button type="button" onClick={() => setSelectedId(scenario.id)} className="text-left font-medium hover:text-accent">
                {scenario.name}
              </button>,
              String(scenario.summary_json.scenario_family ?? "n/a"),
              String(scenario.summary_json.strategy ?? "n/a"),
              formatTimestamp(scenario.updated_at),
            ])}
          />
        )}
      </Panel>
      <Panel title={selected ? "Edit Scenario" : "Create Scenario"} description="Adjust the high-value scenario parameters used most often by operators.">
        <div className="grid gap-4 md:grid-cols-2">
          {[
            ["name", "Scenario name"],
            ["width", "Map width"],
            ["height", "Map height"],
            ["numDrones", "Drone count"],
            ["strategy", "Strategy"],
            ["weather", "Weather"],
            ["maxSteps", "Max steps"],
            ["battery", "Battery"],
            ["returnThreshold", "Reserve threshold"],
            ["coordinationMode", "Coordination mode"],
          ].map(([key, label]) => (
            <label key={key} className="space-y-2 text-sm text-muted">
              <span>{label}</span>
              <input className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white" value={form[key] ?? ""} onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))} />
            </label>
          ))}
        </div>
        <button type="button" onClick={() => saveScenario.mutate()} className="mt-5 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300">
          {selected ? "Update Scenario" : "Create Scenario"}
        </button>
      </Panel>
    </div>
  );
}
