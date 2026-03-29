import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useComparisons, useLibraryTemplates, usePlans, useRuns, useScenarios } from "@/api/hooks";
import type { RunRecord, Snapshot } from "@/api/types";
import { EventTimeline } from "@/components/mission/EventTimeline";
import { MissionSnapshotMap } from "@/components/mission/MissionSnapshotMap";
import { DataTable } from "@/components/ui/DataTable";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { InlineHint } from "@/components/ui/InlineHint";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatTimestamp } from "@/lib/format";

const activeStatuses = new Set(["queued", "running", "paused"]);
const strategyOptions = [
  "information_gain",
  "auction_based",
  "probability_greedy",
  "sector_search",
  "random_sweep",
];

export function MissionControlPage() {
  const queryClient = useQueryClient();
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
    mutationFn: async () => {
      const payload: Record<string, unknown> = { seed: Number(seed) || undefined };
      if (launchSource === "plan") payload.plan_id = launchValue;
      if (launchSource === "scenario") payload.scenario_id = launchValue;
      if (launchSource === "comparison") {
        if (!launchValue || !candidateId) {
          throw new Error("Select both a comparison and a candidate plan.");
        }
        return api.launchComparisonRun(launchValue, {
          candidate_id: candidateId,
          seed: Number(seed) || undefined,
        });
      }
      if (launchSource === "template") payload.template_id = launchValue;
      return api.launchRun(payload);
    },
    onSuccess: async (run) => {
      setSelectedId(run.id);
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const intervention = useMutation({
    mutationFn: ({ action, payload }: { action: string; payload?: Record<string, unknown> }) =>
      api.intervene(selected!.id, { action, payload }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["runs"] });
      if (selected?.id) {
        await queryClient.invalidateQueries({ queryKey: ["events", selected.id] });
      }
    },
  });

  if (isLoading) return <LoadingState label="Loading mission control..." />;
  if (error) return <ErrorState message={(error as Error).message} />;

  const latestSnapshot = (selected?.latest_snapshot_json as Snapshot | null | undefined) ?? undefined;
  const replayFrames = (replayQuery.data?.replay as Snapshot[] | undefined) ?? [];
  const liveSnapshot = replayFrames[replayFrames.length - 1] ?? latestSnapshot;
  const recentEvents = eventsQuery.data?.events ?? [];
  const selectedComparison = comparisons.find((item) => item.id === launchValue);

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Execution workspace"
        title="Mission control"
        description="Launch a simulation from a plan or doctrine baseline, monitor the live mission state, and apply controlled interventions while the run is active."
        actions={
          <>
            <button type="button" onClick={() => launchRun.mutate()} className="primary-button">
              Launch mission run
            </button>
            <button
              type="button"
              onClick={() => selected?.id && setSelectedId(selected.id)}
              className="secondary-button"
            >
              Focus latest run
            </button>
          </>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Active Runs" value={runs.filter((run) => activeStatuses.has(run.status)).length} />
        <MetricCard label="Queued Jobs" value={runs.filter((run) => run.status === "queued").length} />
        <MetricCard label="Completed Runs" value={runs.filter((run) => run.status === "completed").length} />
        <MetricCard
          label="Selected Strategy"
          value={String(selected?.summary_json.strategy ?? "n/a")}
          hint={selected ? `Updated ${formatTimestamp(selected.updated_at)}` : "Select a run to inspect it."}
          emphasis="accent"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <Panel
          eyebrow="Launch flow"
          title="Create a monitored mission run"
          description="Choose the source of truth for this launch. Mission plans and saved comparison candidates are the fastest path to a clean demo."
        >
          <div className="grid gap-4 md:grid-cols-2">
            <label>
              <span className="field-label">Launch source</span>
              <select
                className="field-input"
                value={launchSource}
                onChange={(event) => {
                  setLaunchSource(event.target.value as typeof launchSource);
                  setLaunchValue("");
                  setCandidateId("");
                }}
              >
                <option value="plan">Mission plan</option>
                <option value="scenario">Scenario</option>
                <option value="comparison">Comparison candidate</option>
                <option value="template">Doctrine template</option>
              </select>
            </label>
            <label>
              <span className="field-label">Seed</span>
              <input className="field-input" value={seed} onChange={(event) => setSeed(event.target.value)} />
            </label>
          </div>

          <label className="mt-4 block">
            <span className="field-label">Source selection</span>
            <select className="field-input" value={launchValue} onChange={(event) => setLaunchValue(event.target.value)}>
              <option value="">Select source</option>
              {getLaunchOptions(launchSource, plans, scenarios, comparisons, templates).map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <InlineHint>
            Primary action: choose the most complete source you have. Mission plans and saved comparison candidates
            preserve the cleanest planning intent.
          </InlineHint>

          {launchSource === "comparison" && (
            <label className="mt-4 block">
              <span className="field-label">Candidate plan</span>
              <select className="field-input" value={candidateId} onChange={(event) => setCandidateId(event.target.value)}>
                <option value="">Select candidate</option>
                {(selectedComparison?.candidates ?? []).map((candidate) => (
                  <option key={candidate.id} value={candidate.id}>
                    {candidate.rank}. {candidate.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {launchRun.error ? <ErrorState message={(launchRun.error as Error).message} /> : null}
        </Panel>

        <Panel
          eyebrow="Run queue"
          title="Mission lifecycle"
          description="Pick the run you want to monitor. The live workspace below refreshes automatically while the selected run is active."
        >
          {runs.length === 0 ? (
            <EmptyState
              title="No runs yet"
              body="Launch a monitored run from a mission plan or comparison candidate to activate the execution workflow."
            />
          ) : (
            <DataTable
              columns={["Run", "Status", "Source", "Progress", "Updated"]}
              rows={runs.map((run) => [
                <button
                  type="button"
                  onClick={() => setSelectedId(run.id)}
                  className="text-left font-medium hover:text-accentStrong"
                >
                  {run.id}
                </button>,
                <StatusBadge status={run.status} />,
                run.plan_id ?? run.comparison_id ?? run.scenario_id,
                <div className="min-w-40 space-y-2">
                  <ProgressBar value={run.job?.progress ?? 0} />
                  <span className="text-xs uppercase tracking-[0.14em] text-muted">
                    {Math.round((run.job?.progress ?? 0) * 100)}%
                  </span>
                </div>,
                formatTimestamp(run.updated_at),
              ])}
            />
          )}
        </Panel>
      </div>

      {selected ? (
        <>
          <Panel
            eyebrow="Live run"
            title={`Monitoring ${selected.id}`}
            description="This workspace separates current mission state from operator actions so it is always clear what is happening versus what you can do next."
          >
            <div className="grid gap-4 xl:grid-cols-[1.35fr_0.95fr]">
              <div className="space-y-5">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusBadge status={selected.status} />
                  <span className="pill">{selected.plan_id ? `plan:${selected.plan_id}` : "ad hoc run"}</span>
                  <span className="pill">{String(selected.summary_json.scenario_family ?? "mixed_terrain")}</span>
                  <span className="pill">{String(selected.summary_json.strategy ?? "n/a")}</span>
                </div>
                <div className="panel-subtle p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="section-kicker">Job progress</p>
                      <p className="mt-1 text-sm text-muted">Updated {formatTimestamp(selected.updated_at)}</p>
                    </div>
                    <span className="text-sm font-medium text-white">
                      {Math.round((selected.job?.progress ?? 0) * 100)}%
                    </span>
                  </div>
                  <div className="mt-4">
                    <ProgressBar value={selected.job?.progress ?? 0} />
                  </div>
                </div>

                {liveSnapshot ? (
                  <>
                    <MissionSnapshotMap snapshot={liveSnapshot} />
                    <div className="grid gap-4 md:grid-cols-4">
                      <MetricCard label="Step" value={liveSnapshot.step} />
                      <MetricCard label="Weather" value={liveSnapshot.weather} />
                      <MetricCard label="Assets" value={liveSnapshot.drones.length} />
                      <MetricCard
                        label="Detection"
                        value={liveSnapshot.target_detected ? "Confirmed" : "Searching"}
                        emphasis={liveSnapshot.target_detected ? "accent" : "default"}
                      />
                    </div>
                  </>
                ) : (
                  <EmptyState
                    title="Snapshot pending"
                    body="The run exists, but it has not yet emitted a live snapshot. If it remains in this state, check the queue and event feed."
                  />
                )}
              </div>

              <div className="space-y-4">
                <DetailPanel
                  title="Run context"
                  items={[
                    { label: "Run ID", value: selected.id },
                    { label: "Plan", value: selected.plan_id ?? "n/a" },
                    { label: "Comparison", value: selected.comparison_id ?? "n/a" },
                    { label: "Scenario family", value: String(selected.summary_json.scenario_family ?? "n/a") },
                    { label: "Coordination", value: String(selected.summary_json.coordination_mode ?? "n/a") },
                  ]}
                />
                <Panel
                  eyebrow="Mission metrics"
                  title="Current operational summary"
                  description="These values update as the run progresses and provide a fast sense of mission health."
                >
                  <pre className="whitespace-pre-wrap text-xs leading-6 text-muted">
                    {JSON.stringify(selected.summary_json, null, 2)}
                  </pre>
                </Panel>
              </div>
            </div>
          </Panel>

          <div className="grid gap-6 xl:grid-cols-[0.98fr_1.02fr]">
            <Panel
              eyebrow="Operator actions"
              title="Interventions"
              description="Use interventions deliberately. Each action is recorded in the event stream and replay artifacts."
            >
              <div className="grid gap-3 md:grid-cols-3">
                {[
                  { label: "Pause", action: "pause" },
                  { label: "Resume", action: "resume" },
                  { label: "Force return", action: "force_return", payload: { drone_id: Number(interventionPayload.droneId) } },
                ].map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => intervention.mutate({ action: item.action, payload: item.payload })}
                    className="secondary-button"
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <label>
                  <span className="field-label">Drone ID</span>
                  <input
                    className="field-input"
                    value={interventionPayload.droneId}
                    onChange={(event) =>
                      setInterventionPayload((current) => ({ ...current, droneId: event.target.value }))
                    }
                  />
                </label>
                <label>
                  <span className="field-label">Switch strategy</span>
                  <select
                    className="field-input"
                    value={interventionPayload.strategy}
                    onChange={(event) =>
                      setInterventionPayload((current) => ({ ...current, strategy: event.target.value }))
                    }
                  >
                    {strategyOptions.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label>
                  <span className="field-label">Waypoint X</span>
                  <input
                    className="field-input"
                    value={interventionPayload.waypointX}
                    onChange={(event) =>
                      setInterventionPayload((current) => ({ ...current, waypointX: event.target.value }))
                    }
                  />
                </label>
                <label>
                  <span className="field-label">Waypoint Y</span>
                  <input
                    className="field-input"
                    value={interventionPayload.waypointY}
                    onChange={(event) =>
                      setInterventionPayload((current) => ({ ...current, waypointY: event.target.value }))
                    }
                  />
                </label>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() =>
                    intervention.mutate({
                      action: "assign_waypoint",
                      payload: {
                        drone_id: Number(interventionPayload.droneId),
                        waypoint: [Number(interventionPayload.waypointX), Number(interventionPayload.waypointY)],
                      },
                    })
                  }
                  className="secondary-button"
                >
                  Assign waypoint
                </button>
                <button
                  type="button"
                  onClick={() =>
                    intervention.mutate({
                      action: "switch_strategy",
                      payload: { strategy: interventionPayload.strategy },
                    })
                  }
                  className="secondary-button"
                >
                  Apply strategy switch
                </button>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <label>
                  <span className="field-label">Priority zone JSON</span>
                  <textarea
                    className="field-textarea"
                    value={interventionPayload.priorityZone}
                    onChange={(event) =>
                      setInterventionPayload((current) => ({ ...current, priorityZone: event.target.value }))
                    }
                  />
                </label>
                <label>
                  <span className="field-label">Exclusion zone JSON</span>
                  <textarea
                    className="field-textarea"
                    value={interventionPayload.exclusionZone}
                    onChange={(event) =>
                      setInterventionPayload((current) => ({ ...current, exclusionZone: event.target.value }))
                    }
                  />
                </label>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <button
                  type="button"
                  onClick={() =>
                    intervention.mutate({
                      action: "set_priority_zone",
                      payload: safeJson(interventionPayload.priorityZone),
                    })
                  }
                  className="secondary-button"
                >
                  Add priority zone
                </button>
                <button
                  type="button"
                  onClick={() =>
                    intervention.mutate({
                      action: "set_exclusion_zone",
                      payload: safeJson(interventionPayload.exclusionZone),
                    })
                  }
                  className="secondary-button"
                >
                  Add exclusion zone
                </button>
              </div>
              {intervention.error ? <ErrorState message={(intervention.error as Error).message} /> : null}
            </Panel>

            <Panel
              eyebrow="Event feed"
              title="What changed recently"
              description="The event stream is the fastest way to understand status changes, detections, reroutes, and operator interventions."
            >
              {recentEvents.length === 0 ? (
                <EmptyState
                  title="No events yet"
                  body="Events will appear here once the run starts stepping or receives interventions."
                />
              ) : (
                <EventTimeline events={recentEvents.slice(-12).reverse()} />
              )}
            </Panel>
          </div>
        </>
      ) : (
        <EmptyState
          title="No run selected"
          body="Launch a run from a mission plan or comparison candidate to activate the monitoring workspace."
        />
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
