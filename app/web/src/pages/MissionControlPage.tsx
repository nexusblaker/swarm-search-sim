import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useComparisons, useLibraryTemplates, usePlans, useRuns, useScenarios } from "@/api/hooks";
import type { RunRecord, Snapshot } from "@/api/types";
import { EventTimeline } from "@/components/mission/EventTimeline";
import { MissionSnapshotMap } from "@/components/mission/MissionSnapshotMap";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { Panel } from "@/components/ui/Panel";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

const activeStatuses = new Set(["queued", "running", "paused"]);

export function MissionControlPage() {
  const { data: runsData, isLoading, error } = useRuns(3000);
  const { data: plansData } = usePlans();
  const { data: scenariosData } = useScenarios();
  const { data: comparisonsData } = useComparisons();
  const { data: templatesData } = useLibraryTemplates();
  const runs = runsData?.items ?? [];
  const plans = plansData?.items ?? [];
  const scenarios = scenariosData?.items ?? [];
  const comparisons = comparisonsData?.items ?? [];
  const templates = templatesData?.items ?? [];
  const [selectedId, setSelectedId] = useState<string>("");
  const [launchSource, setLaunchSource] = useState<"plan" | "scenario" | "comparison" | "template">("plan");
  const [launchValue, setLaunchValue] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [seed, setSeed] = useState("7");
  const [interventionPayload, setInterventionPayload] = useState({
    droneId: "0",
    waypointX: "5",
    waypointY: "5",
    priorityZone: '{"center":[6,6],"radius":3}',
    exclusionZone: '{"center":[2,2],"radius":2}',
    strategy: "information_gain",
  });

  useEffect(() => {
    if (!selectedId && runs[0]) {
      setSelectedId(runs[0].id);
    }
  }, [runs, selectedId]);

  const selected = useMemo<RunRecord | undefined>(
    () => runs.find((run) => run.id === selectedId) ?? runs[0],
    [runs, selectedId],
  );

  const replayQuery = useQuery({
    queryKey: ["replay", selected?.id],
    queryFn: () => api.replay(selected!.id),
    enabled: Boolean(selected?.id),
    refetchInterval: activeStatuses.has(selected?.status ?? "") ? 3000 : false,
  });

  const eventsQuery = useQuery({
    queryKey: ["events", selected?.id],
    queryFn: () => api.events(selected!.id),
    enabled: Boolean(selected?.id),
    refetchInterval: activeStatuses.has(selected?.status ?? "") ? 3000 : false,
  });

  const launchRun = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = { seed: Number(seed) || undefined };
        if (launchSource === "plan") payload.plan_id = launchValue;
        if (launchSource === "scenario") payload.scenario_id = launchValue;
        if (launchSource === "comparison") {
          if (!launchValue || !candidateId) {
            throw new Error("Select both a comparison and a candidate plan.");
          }
          return api.launchComparisonRun(launchValue, { candidate_id: candidateId, seed: Number(seed) || undefined });
        }
        if (launchSource === "template") payload.template_id = launchValue;
        return api.launchRun(payload);
      },
  });

  const intervention = useMutation({
    mutationFn: ({ action, payload }: { action: string; payload?: Record<string, unknown> }) =>
      api.intervene(selected!.id, { action, payload }),
  });

  if (isLoading) return <LoadingState label="Loading mission control..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  const latestSnapshot = (selected?.latest_snapshot_json as Snapshot | null | undefined) ?? undefined;
  const replayFrames = (replayQuery.data?.replay as Snapshot[] | undefined) ?? [];
  const liveSnapshot = replayFrames[replayFrames.length - 1] ?? latestSnapshot;
  const recentEvents = eventsQuery.data?.events ?? [];
  const selectedComparison = comparisons.find((item) => item.id === launchValue);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Active Runs" value={runs.filter((run) => activeStatuses.has(run.status)).length} />
        <MetricCard label="Queued Jobs" value={runs.filter((run) => run.status === "queued").length} />
        <MetricCard label="Completed Runs" value={runs.filter((run) => run.status === "completed").length} />
        <MetricCard label="Latest Strategy" value={String(selected?.summary_json.strategy ?? "n/a")} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.25fr]">
        <Panel title="Launch Mission" description="Launch from a mission plan, scenario, saved comparison, or doctrine template.">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-muted">
              <span>Launch source</span>
              <select
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={launchSource}
                onChange={(event) => {
                  setLaunchSource(event.target.value as typeof launchSource);
                  setLaunchValue("");
                  setCandidateId("");
                }}
              >
                <option value="plan">Mission plan</option>
                <option value="scenario">Scenario</option>
                <option value="comparison">Saved comparison</option>
                <option value="template">Template</option>
              </select>
            </label>
            <label className="space-y-2 text-sm text-muted">
              <span>Seed</span>
              <input
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={seed}
                onChange={(event) => setSeed(event.target.value)}
              />
            </label>
          </div>
          <label className="mt-4 block space-y-2 text-sm text-muted">
            <span>Selected source</span>
            <select
              className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
              value={launchValue}
              onChange={(event) => setLaunchValue(event.target.value)}
            >
              <option value="">Select…</option>
              {getLaunchOptions(launchSource, plans, scenarios, comparisons, templates).map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {launchSource === "comparison" && (
            <label className="mt-4 block space-y-2 text-sm text-muted">
              <span>Candidate plan</span>
              <select
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                value={candidateId}
                onChange={(event) => setCandidateId(event.target.value)}
              >
                <option value="">Select candidate…</option>
                {(selectedComparison?.candidates ?? []).map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.rank}. {candidate.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button
            type="button"
            onClick={() => launchRun.mutate()}
            className="mt-5 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300"
          >
            Launch Mission Run
          </button>
        </Panel>

        <Panel title="Run Queue" description="Active and historical run lifecycle with current job progress.">
          {runs.length === 0 ? (
            <EmptyState title="No runs yet" body="Launch a run to start the live mission workflow." />
          ) : (
            <DataTable
              columns={["Run", "Status", "Plan", "Progress", "Updated"]}
              rows={runs.map((run) => [
                <button
                  type="button"
                  onClick={() => setSelectedId(run.id)}
                  className="text-left font-medium hover:text-accent"
                >
                  {run.id}
                </button>,
                <StatusBadge status={run.status} />,
                run.plan_id ?? run.comparison_id ?? run.scenario_id,
                <div className="w-32">
                  <ProgressBar value={Math.round((run.job?.progress ?? 0) * 100)} />
                </div>,
                formatTimestamp(run.updated_at),
              ])}
            />
          )}
        </Panel>
      </div>

      {selected && (
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.95fr]">
          <Panel title="Live Mission Snapshot" description="Latest mission state, belief overlay, assets, and target estimate.">
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <StatusBadge status={selected.status} />
              <span className="text-sm text-muted">Updated {formatTimestamp(selected.updated_at)}</span>
              <div className="min-w-[240px] flex-1">
                <ProgressBar value={Math.round((selected.job?.progress ?? 0) * 100)} />
              </div>
            </div>
            {liveSnapshot ? (
              <div className="space-y-4">
                <MissionSnapshotMap snapshot={liveSnapshot} />
                <div className="grid gap-4 md:grid-cols-4">
                  <MetricCard label="Step" value={liveSnapshot.step} />
                  <MetricCard label="Weather" value={liveSnapshot.weather} />
                  <MetricCard label="Strategy" value={liveSnapshot.strategy} />
                  <MetricCard
                    label="Detection"
                    value={liveSnapshot.target_detected ? "Confirmed" : "Searching"}
                  />
                </div>
              </div>
            ) : (
              <EmptyState title="No snapshot yet" body="The run is queued or has not emitted state yet." />
            )}
          </Panel>

          <Panel title="Mission Control Actions" description="Pause, resume, redirect, and update priorities while the run is active.">
            <div className="grid gap-3 md:grid-cols-2">
              {[
                { label: "Pause", action: "pause" },
                { label: "Resume", action: "resume" },
                { label: "Force Return", action: "force_return", payload: { drone_id: Number(interventionPayload.droneId) } },
              ].map((item) => (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => intervention.mutate({ action: item.action, payload: item.payload })}
                  className="rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-sm font-medium text-white hover:border-accent/40 hover:text-accent"
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="mt-5 space-y-4">
              <label className="block space-y-2 text-sm text-muted">
                <span>Drone ID</span>
                <input
                  className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                  value={interventionPayload.droneId}
                  onChange={(event) =>
                    setInterventionPayload((current) => ({ ...current, droneId: event.target.value }))
                  }
                />
              </label>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm text-muted">
                  <span>Waypoint X</span>
                  <input
                    className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                    value={interventionPayload.waypointX}
                    onChange={(event) =>
                      setInterventionPayload((current) => ({ ...current, waypointX: event.target.value }))
                    }
                  />
                </label>
                <label className="space-y-2 text-sm text-muted">
                  <span>Waypoint Y</span>
                  <input
                    className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                    value={interventionPayload.waypointY}
                    onChange={(event) =>
                      setInterventionPayload((current) => ({ ...current, waypointY: event.target.value }))
                    }
                  />
                </label>
              </div>
              <button
                type="button"
                onClick={() =>
                  intervention.mutate({
                    action: "assign_waypoint",
                    payload: {
                      drone_id: Number(interventionPayload.droneId),
                      waypoint: [
                        Number(interventionPayload.waypointX),
                        Number(interventionPayload.waypointY),
                      ],
                    },
                  })
                }
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-sm font-medium text-white hover:border-accent/40 hover:text-accent"
              >
                Assign Waypoint
              </button>

              <label className="block space-y-2 text-sm text-muted">
                <span>Priority zone JSON</span>
                <textarea
                  className="min-h-24 w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                  value={interventionPayload.priorityZone}
                  onChange={(event) =>
                    setInterventionPayload((current) => ({ ...current, priorityZone: event.target.value }))
                  }
                />
              </label>
              <div className="grid gap-3 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() =>
                    intervention.mutate({
                      action: "set_priority_zone",
                      payload: safeJson(interventionPayload.priorityZone),
                    })
                  }
                  className="rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-sm font-medium text-white hover:border-accent/40 hover:text-accent"
                >
                  Add Priority Zone
                </button>
                <button
                  type="button"
                  onClick={() =>
                    intervention.mutate({
                      action: "set_exclusion_zone",
                      payload: safeJson(interventionPayload.exclusionZone),
                    })
                  }
                  className="rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-sm font-medium text-white hover:border-accent/40 hover:text-accent"
                >
                  Add Exclusion Zone
                </button>
              </div>

              <label className="block space-y-2 text-sm text-muted">
                <span>Exclusion zone JSON</span>
                <textarea
                  className="min-h-24 w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                  value={interventionPayload.exclusionZone}
                  onChange={(event) =>
                    setInterventionPayload((current) => ({ ...current, exclusionZone: event.target.value }))
                  }
                />
              </label>

              <label className="block space-y-2 text-sm text-muted">
                <span>Switch strategy</span>
                <select
                  className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
                  value={interventionPayload.strategy}
                  onChange={(event) =>
                    setInterventionPayload((current) => ({ ...current, strategy: event.target.value }))
                  }
                >
                  <option value="information_gain">information_gain</option>
                  <option value="auction_based">auction_based</option>
                  <option value="probability_greedy">probability_greedy</option>
                  <option value="sector_search">sector_search</option>
                  <option value="random_sweep">random_sweep</option>
                </select>
              </label>
              <button
                type="button"
                onClick={() =>
                  intervention.mutate({
                    action: "switch_strategy",
                    payload: { strategy: interventionPayload.strategy },
                  })
                }
                className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-sm font-medium text-white hover:border-accent/40 hover:text-accent"
              >
                Apply Strategy Switch
              </button>
            </div>
          </Panel>
        </div>
      )}

      {selected && (
        <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
          <Panel title="Mission Metrics" description="Latest metrics emitted by the active or completed run.">
            <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
              {JSON.stringify(selected.summary_json, null, 2)}
            </pre>
          </Panel>
          <Panel title="Recent Event Feed" description="Latest replay and telemetry events for operator awareness.">
            {recentEvents.length === 0 ? (
              <EmptyState title="No events yet" body="Events appear here once the run starts stepping or receives interventions." />
            ) : (
              <EventTimeline events={recentEvents.slice(-10).reverse()} />
            )}
          </Panel>
        </div>
      )}
    </div>
  );
}

function getLaunchOptions(
  source: "plan" | "scenario" | "comparison" | "template",
  plans: Array<{ id: string; name: string }>,
  scenarios: Array<{ id: string; name: string }>,
  comparisons: Array<{ id: string; name: string }>,
  templates: Array<{ id: string; name: string }>,
) {
  if (source === "plan") return plans.map((item) => ({ id: item.id, label: item.name }));
  if (source === "scenario") return scenarios.map((item) => ({ id: item.id, label: item.name }));
  if (source === "comparison") return comparisons.map((item) => ({ id: item.id, label: item.name }));
  return templates.map((item) => ({ id: item.id, label: item.name }));
}

function safeJson(value: string): Record<string, unknown> {
  try {
    return JSON.parse(value) as Record<string, unknown>;
  } catch {
    return {};
  }
}
