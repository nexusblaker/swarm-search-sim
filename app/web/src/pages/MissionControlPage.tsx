import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useComparisons, useLibraryTemplates, usePlans, useRuns, useScenarios } from "@/api/hooks";
import type {
  CandidateContact,
  LifecycleSummaryRecord,
  RunRecord,
  RunSummaryRecord,
  Snapshot,
  SnapshotDrone,
} from "@/api/types";
import { EventTimeline } from "@/components/mission/EventTimeline";
import { MissionSnapshotMap } from "@/components/mission/MissionSnapshotMap";
import { DataTable } from "@/components/ui/DataTable";
import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel";
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
import { batteryBarClass, formatBatteryPercent, formatStepEta, reserveStatusLabel, serviceEtaLabel } from "@/lib/lifecycle";
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
  const runSummary = (selected?.summary_json ?? {}) as RunSummaryRecord;
  const lifecycleSummary = (liveSnapshot?.lifecycle_summary ?? runSummary.lifecycle_summary ?? {}) as LifecycleSummaryRecord;
  const sensingSummary = (liveSnapshot?.sensing_summary ?? runSummary.sensing_summary ?? {}) as Record<string, unknown>;
  const liveDrones = liveSnapshot?.drones ?? [];
  const candidateContacts = (liveSnapshot?.candidate_contacts ?? []) as CandidateContact[];
  const activeSearchCount = Array.isArray(liveSnapshot?.active_search_drones)
    ? liveSnapshot?.active_search_drones.length
    : Number(
        lifecycleSummary.active_search_drones ??
          liveDrones.filter((drone) => Boolean(drone.contributing_to_search)).length,
      );
  const returningCount = Number(
    lifecycleSummary.returning_drones ??
      liveDrones.filter((drone) => drone.lifecycle_state === "returning_to_base").length,
  );
  const rechargingCount = Number(
    lifecycleSummary.recharging_drones ??
      liveDrones.filter((drone) => drone.lifecycle_state === "recharging_or_swapping").length,
  );
  const readyCount = Number(
    lifecycleSummary.ready_to_redeploy ??
      liveDrones.filter((drone) => drone.lifecycle_state === "ready_to_redeploy").length,
  );
  const runPhase = String(liveSnapshot?.run_phase ?? lifecycleSummary.run_phase ?? runSummary.run_phase ?? "Active search");
  const reservePreset = String(lifecycleSummary.reserve_preset ?? runSummary.reserve_preset ?? "balanced");
  const contactsUnderInspection = Number(sensingSummary.contacts_under_inspection ?? 0);
  const candidateContactCount = Number(sensingSummary.active_candidate_contacts ?? candidateContacts.length);
  const confirmedContactCount = Number(sensingSummary.confirmed_contact_count ?? 0);
  const sensingNarrative = String(
    sensingSummary.operator_summary ?? "No active contacts are awaiting confirmation.",
  );

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
        <MetricCard label="Mission Phase" value={selected ? runPhase : "Waiting"} emphasis="accent" />
        <MetricCard label="Active Search Assets" value={selected ? activeSearchCount : 0} />
        <MetricCard
          label="Contact Workflow"
          value={
            selected
              ? contactsUnderInspection > 0
                ? `${contactsUnderInspection} inspecting`
                : candidateContactCount > 0
                  ? `${candidateContactCount} possible`
                  : confirmedContactCount > 0
                    ? "Confirmed"
                    : "Clear"
              : "Waiting"
          }
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
            description="Keep the mission visual anchored on the left, then open the right-side modules only when you need more operational detail."
          >
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_390px]">
              <div className="space-y-5 xl:sticky xl:top-[7.5rem] xl:self-start">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusBadge status={selected.status} />
                  <span className="pill">{selected.plan_id ? `Plan ${selected.plan_id}` : "Ad hoc run"}</span>
                  <span className="pill">{String(runSummary.scenario_family ?? "mixed terrain").replaceAll("_", " ")}</span>
                  <span className="pill">{String(runSummary.strategy ?? "n/a").replaceAll("_", " ")}</span>
                  <span className="pill">{reservePreset.replaceAll("_", " ")}</span>
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
                <div className="grid gap-4 md:grid-cols-4">
                  <MetricCard label="Mission Phase" value={runPhase} emphasis="accent" />
                  <MetricCard label="Contact State" value={confirmedContactCount > 0 ? "Confirmed" : candidateContactCount > 0 ? "Investigating" : "Searching"} />
                  <MetricCard label="Active Assets" value={activeSearchCount} />
                  <MetricCard label="Returning / service" value={`${returningCount + rechargingCount}`} />
                </div>

                {liveSnapshot ? (
                  <>
                    <MissionSnapshotMap snapshot={liveSnapshot} />
                    <div className="rounded-[24px] border border-border/70 bg-surfaceAlt/50 p-5">
                      <p className="section-kicker">Mission story</p>
                      <p className="mt-3 text-base leading-7 text-white">
                        {confirmedContactCount > 0
                          ? "A contact has been confirmed. Keep attention on the latest event feed and active asset assignment."
                          : candidateContactCount > 0
                            ? sensingNarrative
                            : lifecycleSummary.coverage_gap_active
                              ? "The mission is managing temporary coverage loss while assets rotate through return and service."
                              : "The mission remains in broad search with coverage holding steady across the active fleet."}
                      </p>
                      <div className="mt-4 grid gap-3 md:grid-cols-4">
                        <RotationStat label="Step" value={liveSnapshot.step} />
                        <RotationStat label="Returning to base" value={returningCount} />
                        <RotationStat label="Recharging" value={rechargingCount} />
                        <RotationStat label="Ready to redeploy" value={readyCount} />
                      </div>
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
                <CollapsiblePanel
                  title="Mission context"
                  description="Open the plan, coordination, and reserve context behind this live run."
                >
                  <DetailPanel
                    title="Run context"
                    items={[
                      { label: "Run ID", value: selected.id },
                      { label: "Plan", value: selected.plan_id ?? "n/a" },
                      { label: "Comparison", value: selected.comparison_id ?? "n/a" },
                      { label: "Scenario family", value: String(runSummary.scenario_family ?? "n/a").replaceAll("_", " ") },
                      { label: "Team coordination", value: String(runSummary.coordination_mode ?? "n/a").replaceAll("_", " ") },
                      { label: "Reserve policy", value: reservePreset.replaceAll("_", " ") },
                      { label: "Run phase", value: runPhase },
                    ]}
                  />
                  <div className="mt-4 rounded-[20px] border border-border/70 bg-surfaceAlt/55 p-4">
                    <p className="section-kicker">Battery rotation</p>
                    <p className="mt-3 text-sm leading-6 text-muted">
                      {lifecycleSummary.coverage_gap_active
                        ? "The mission is compensating for temporary coverage loss while assets rotate through base."
                        : "Coverage remains stable while the fleet cycles through search, return, service, and redeploy."}
                    </p>
                  </div>
                </CollapsiblePanel>

                <CollapsiblePanel
                  title="Contact workflow"
                  description="Track possible contacts, inspections, and confirmed detections."
                >
                  <div className="grid gap-3 sm:grid-cols-3">
                    <RotationStat label="Possible contacts" value={candidateContactCount} />
                    <RotationStat label="Inspecting now" value={contactsUnderInspection} />
                    <RotationStat label="Confirmed" value={confirmedContactCount} />
                  </div>
                  <p className="mt-4 text-sm leading-6 text-muted">{sensingNarrative}</p>
                  {candidateContacts.length > 0 ? (
                    <div className="mt-4 space-y-2">
                      {candidateContacts.slice(0, 3).map((contact) => (
                        <div key={contact.id} className="rounded-[16px] border border-border/70 bg-surfaceAlt/55 px-4 py-3">
                          <p className="text-sm font-medium text-white">{contact.status_label ?? "Possible Contact"}</p>
                          <p className="mt-1 text-sm text-muted">{contact.note ?? "Contact awaiting inspection details."}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 text-sm leading-6 text-muted">No active contact investigation is underway right now.</p>
                  )}
                </CollapsiblePanel>

                <CollapsiblePanel
                  title="Fleet roster"
                  description="See which drones are searching, rotating through base, or ready to rejoin coverage."
                  defaultOpen={false}
                >
                  <div className="space-y-3">
                    {liveDrones.length === 0 ? (
                      <p className="text-sm text-muted">Drone status will appear once the run emits a snapshot.</p>
                    ) : (
                      liveDrones.map((drone) => <DroneRosterCard key={drone.id} drone={drone} />)
                    )}
                  </div>
                </CollapsiblePanel>

                <CollapsiblePanel
                  title="Interventions"
                  description="Use these sparingly. Each action is recorded in the event feed and replay."
                  defaultOpen={false}
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
                </CollapsiblePanel>

                <CollapsiblePanel
                  title="Recent events"
                  description="See what changed most recently and why the mission shifted."
                >
                  {recentEvents.length === 0 ? (
                    <EmptyState
                      title="No events yet"
                      body="Events will appear here once the run starts stepping or receives interventions."
                    />
                  ) : (
                    <EventTimeline events={recentEvents.slice(-12).reverse()} />
                  )}
                </CollapsiblePanel>

                <CollapsiblePanel
                  title="Technical details"
                  description="Open the structured run summary behind this live view."
                  defaultOpen={false}
                >
                  <pre className="whitespace-pre-wrap text-xs leading-6 text-muted">
                    {JSON.stringify(runSummary, null, 2)}
                  </pre>
                </CollapsiblePanel>
              </div>
            </div>
          </Panel>
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

function DroneRosterCard({ drone }: { drone: SnapshotDrone }) {
  const batteryPct = typeof drone.battery_pct === "number" ? drone.battery_pct : drone.battery;
  const coverageStatus = drone.contributing_to_search ? "Contributing to coverage" : "Temporarily off broad search";

  return (
    <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-white">Drone {drone.id}</p>
          <p className="mt-1 text-sm text-muted">{drone.operator_status ?? "Status unavailable"}</p>
        </div>
        <span className="pill whitespace-nowrap">
          {drone.reserve_status_label ?? reserveStatusLabel(drone.reserve_status)}
        </span>
      </div>
      <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full transition-all ${batteryBarClass(batteryPct)}`}
          style={{ width: `${Math.max(0, Math.min(100, Number(batteryPct ?? 0)))}%` }}
        />
      </div>
      <div className="mt-3 grid gap-2 text-sm text-white/90 md:grid-cols-2">
        <span>Battery: {formatBatteryPercent(batteryPct)}</span>
        <span>{serviceEtaLabel(drone)}</span>
        <span>Return ETA: {formatStepEta(drone.return_eta_steps, "At base")}</span>
        <span>Sorties: {drone.sorties_completed ?? 0}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-white/90">{coverageStatus}</p>
      {drone.assigned_contact_id ? (
        <p className="mt-2 text-sm leading-6 text-muted">Assigned contact: {drone.assigned_contact_id}</p>
      ) : null}
      {drone.reserve_reason ? <p className="mt-3 text-sm leading-6 text-muted">{drone.reserve_reason}</p> : null}
    </div>
  );
}

function RotationStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-[18px] border border-border/70 bg-surfaceAlt/55 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-2 text-lg font-semibold text-white">{value}</p>
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
