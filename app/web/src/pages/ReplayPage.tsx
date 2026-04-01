import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useRuns } from "@/api/hooks";
import type { CandidateContact, LifecycleSummaryRecord, MissionAreaSummary, Snapshot } from "@/api/types";
import { EventTimeline } from "@/components/mission/EventTimeline";
import { MissionSnapshotMap } from "@/components/mission/MissionSnapshotMap";
import { CollapsiblePanel } from "@/components/ui/CollapsiblePanel";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  batteryBarClass,
  eventPresentation,
  formatBatteryPercent,
  isLifecycleEvent,
  serviceEtaLabel,
} from "@/lib/lifecycle";
import { formatTimestamp } from "@/lib/format";

export function ReplayPage() {
  const { data: runsData, isLoading, error } = useRuns();
  const completedRuns = useMemo(
    () => (runsData?.items ?? []).filter((run) => ["completed", "failed", "cancelled"].includes(run.status)),
    [runsData],
  );
  const [runId, setRunId] = useState("");
  const [frameIndex, setFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (!runId && completedRuns[0]) {
      setRunId(completedRuns[0].id);
    }
  }, [completedRuns, runId]);

  useEffect(() => {
    if (!isPlaying) {
      return;
    }
    const timer = window.setInterval(() => {
      setFrameIndex((current) => current + 1);
    }, 700);
    return () => window.clearInterval(timer);
  }, [isPlaying]);

  const replayQuery = useQuery({
    queryKey: ["replay", runId],
    queryFn: () => api.replay(runId),
    enabled: Boolean(runId),
  });
  const eventsQuery = useQuery({
    queryKey: ["events", runId],
    queryFn: () => api.events(runId),
    enabled: Boolean(runId),
  });

  const frames = (replayQuery.data?.replay as Snapshot[] | undefined) ?? [];
  const clampedIndex = Math.min(frameIndex, Math.max(frames.length - 1, 0));
  const frame = frames[clampedIndex];

  useEffect(() => {
    if (frames.length === 0) {
      return;
    }
    if (frameIndex >= frames.length - 1) {
      setIsPlaying(false);
    }
  }, [frameIndex, frames.length]);

  const allEvents = eventsQuery.data?.events ?? [];
  const filteredEvents = allEvents.filter((event) => Number(event.step ?? 0) <= Number(frame?.step ?? 0));
  const lifecycleEvents = allEvents.filter(isLifecycleEvent);
  const selectedRun = completedRuns.find((run) => run.id === runId);
  const lifecycleSummary = (frame?.lifecycle_summary ?? selectedRun?.summary_json.lifecycle_summary ?? {}) as LifecycleSummaryRecord;
  const sensingSummary = (frame?.sensing_summary ?? selectedRun?.summary_json.sensing_summary ?? {}) as Record<string, unknown>;
  const candidateContacts = (frame?.candidate_contacts ?? []) as CandidateContact[];
  const activeSearchCount = Array.isArray(frame?.active_search_drones)
    ? frame.active_search_drones.length
    : Number(
        lifecycleSummary.active_search_drones ??
          frame?.drones.filter((drone) => Boolean(drone.contributing_to_search)).length ??
          0,
      );
  const returningCount = Number(
    lifecycleSummary.returning_drones ??
      frame?.drones.filter((drone) => drone.lifecycle_state === "returning_to_base").length ??
      0,
  );
  const rechargingCount = Number(
    lifecycleSummary.recharging_drones ??
      frame?.drones.filter((drone) => drone.lifecycle_state === "recharging_or_swapping").length ??
      0,
  );
  const runPhase = String(frame?.run_phase ?? lifecycleSummary.run_phase ?? selectedRun?.summary_json.run_phase ?? "Mission replay");
  const searchPatternLabel = String(
    frame?.search_pattern_label ?? selectedRun?.summary_json.search_pattern_label ?? "Search pattern pending",
  );
  const searchPatternSummary = String(
    frame?.search_pattern_summary ?? selectedRun?.summary_json.search_pattern_summary ?? "Pattern summary not recorded for this replay frame.",
  );
  const searchPatternReason = String(
    frame?.search_pattern_reason ?? selectedRun?.summary_json.search_pattern_reason ?? "",
  );
  const searchPatternRebalanced = Boolean(
    frame?.search_pattern_rebalanced ?? selectedRun?.summary_json.search_pattern_rebalanced,
  );
  const searchPatternRebalanceReason = String(
    frame?.search_pattern_rebalance_reason ?? selectedRun?.summary_json.search_pattern_rebalance_reason ?? "",
  );
  const missionArea = (frame?.mission_area ?? selectedRun?.summary_json.mission_area ?? {}) as MissionAreaSummary;
  const missionAreaLabel = String(missionArea.location_display_name ?? "Mission area");
  const missionAreaSummary = String(
    missionArea.operator_summary ?? selectedRun?.summary_json.mission_area_summary ?? "Mission area summary pending.",
  );
  const contactsUnderInspection = Number(sensingSummary.contacts_under_inspection ?? 0);
  const candidateContactCount = Number(sensingSummary.active_candidate_contacts ?? candidateContacts.length);
  const sensingNarrative = String(
    sensingSummary.operator_summary ?? "No active contacts are awaiting confirmation at this step.",
  );

  if (isLoading) return <LoadingState label="Loading replay browser..." />;
  if (error) return <ErrorState message={(error as Error).message} />;
  if (completedRuns.length === 0) {
    return <EmptyState title="No completed runs yet" body="Finish a mission run to explore replay and event playback." />;
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Playback workstation"
        title="Replay"
        description="Inspect a completed mission step by step, scrub the timeline, and correlate state changes with the event feed and mission metrics."
      />

      <Panel
        eyebrow="Selection"
        title="Choose a completed run"
        description="Primary action: select the run you want to inspect, then scrub or play through the mission timeline."
      >
        <div className="grid gap-4 md:grid-cols-[1.4fr_0.7fr_0.7fr]">
          <label>
            <span className="field-label">Completed run</span>
            <select
              className="field-input"
              value={runId}
              onChange={(event) => {
                setRunId(event.target.value);
                setFrameIndex(0);
                setIsPlaying(false);
              }}
            >
              {completedRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.id}
                </option>
              ))}
            </select>
          </label>
          <div className="panel-subtle px-4 py-4">
            <p className="section-kicker">Status</p>
            <div className="mt-2">
              <StatusBadge status={selectedRun?.status ?? "completed"} />
            </div>
          </div>
          <div className="panel-subtle px-4 py-4">
            <p className="section-kicker">Completed</p>
            <p className="mt-2 text-sm text-white">
              {selectedRun?.completed_at ? formatTimestamp(selectedRun.completed_at) : "n/a"}
            </p>
          </div>
        </div>
      </Panel>

      {!frame ? (
        <EmptyState title="Replay is still building" body="This run does not have replay frames available yet." />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Frame" value={`${clampedIndex + 1}/${frames.length}`} />
            <MetricCard label="Run Phase" value={runPhase} emphasis="accent" />
            <MetricCard label="Active Search" value={activeSearchCount} />
            <MetricCard
              label="Contact Workflow"
              value={
                contactsUnderInspection > 0
                  ? `${contactsUnderInspection} inspecting`
                  : candidateContactCount > 0
                    ? `${candidateContactCount} possible`
                    : "Clear"
              }
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.28fr)_390px]">
            <Panel
              eyebrow="Playback"
              title="Mission replay"
              description="Keep the mission visual anchored while you scrub, then open the right-side modules for event detail, roster state, and technical context."
              className="xl:sticky xl:top-[7.5rem] xl:self-start"
            >
              <MissionSnapshotMap snapshot={frame} />
              <div className="mt-5 space-y-4">
                <div className="flex flex-wrap gap-3">
                  <button type="button" onClick={() => setFrameIndex(0)} className="secondary-button">
                    Jump to start
                  </button>
                  <button type="button" onClick={() => setIsPlaying((current) => !current)} className="secondary-button">
                    {isPlaying ? "Pause" : "Play"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setFrameIndex((current) => Math.max(0, current - 1))}
                    className="secondary-button"
                  >
                    Previous step
                  </button>
                  <button
                    type="button"
                    onClick={() => setFrameIndex((current) => Math.min(frames.length - 1, current + 1))}
                    className="secondary-button"
                  >
                    Next step
                  </button>
                </div>
                <input
                  type="range"
                  min={0}
                  max={Math.max(frames.length - 1, 0)}
                  value={clampedIndex}
                  onChange={(event) => {
                    setFrameIndex(Number(event.target.value));
                    setIsPlaying(false);
                  }}
                  className="w-full accent-[#8fb4d6]"
                />
                <div className="rounded-[22px] border border-border/70 bg-surfaceAlt/50 p-4">
                  <p className="section-kicker">Timeline markers</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {lifecycleEvents.slice(0, 10).map((event, index) => {
                      const view = eventPresentation(event);
                      return (
                        <span key={`${String(event.step)}-${index}`} className="pill">
                          Step {String(event.step ?? "?")} | {view.title}
                        </span>
                      );
                    })}
                  </div>
                </div>
              </div>
            </Panel>

            <div className="space-y-4">
              <CollapsiblePanel
                title="Frame summary"
                description="Review the main mission picture at the current step."
              >
                <DetailPanel
                  title="Selected step"
                  items={[
                    { label: "Step", value: frame.step },
                    { label: "Mission phase", value: runPhase },
                    { label: "Mission area", value: missionAreaLabel },
                    { label: "Area size", value: missionArea.area_sq_km ? `${missionArea.area_sq_km.toFixed(1)} km²` : "n/a" },
                    { label: "Search pattern", value: searchPatternLabel },
                    { label: "Strategy", value: frame.strategy },
                    { label: "Team coordination", value: frame.coordination_mode },
                    { label: "Active search assets", value: activeSearchCount },
                    { label: "Possible contacts", value: candidateContactCount },
                    { label: "Coverage gap", value: lifecycleSummary.coverage_gap_active ? "Managing gap" : "Covered" },
                  ]}
                />
                <div className="mt-4 space-y-4">
                  <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/55 p-4">
                    <p className="section-kicker">Mission area</p>
                    <p className="mt-3 text-sm leading-6 text-white/90">{missionAreaSummary}</p>
                    {missionArea.terrain_summary?.operator_summary ? (
                      <p className="mt-3 text-sm leading-6 text-muted">{missionArea.terrain_summary.operator_summary}</p>
                    ) : null}
                  </div>
                  <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/55 p-4">
                    <p className="section-kicker">Search pattern</p>
                    <p className="mt-3 text-sm leading-6 text-white/90">{searchPatternSummary}</p>
                    <p className="mt-3 text-sm leading-6 text-muted">
                      {searchPatternRebalanced
                        ? `Adaptive rebalance is active because ${searchPatternRebalanceReason || "mission conditions changed"}.`
                        : searchPatternReason || "The run is still following its planned pattern."}
                    </p>
                  </div>
                  <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/55 p-4">
                    <p className="section-kicker">Contact workflow</p>
                    <p className="mt-3 text-sm leading-6 text-white/90">{sensingNarrative}</p>
                  </div>
                  <div className="rounded-[20px] border border-border/70 bg-surfaceAlt/55 p-4">
                    <p className="section-kicker">Mission continuity</p>
                    <p className="mt-3 text-sm leading-6 text-white/90">
                      {lifecycleSummary.coverage_gap_active
                        ? "Coverage is thinner at this moment because one or more assets are away from the search area."
                        : "Coverage is currently stable, with returning and redeployed assets balanced into the mission."}
                    </p>
                  </div>
                </div>
              </CollapsiblePanel>

              <CollapsiblePanel
                title="Event stream"
                description="See what happened at or before the current frame."
              >
                {filteredEvents.length === 0 ? (
                  <EmptyState title="No events at this point" body="Move later in the timeline or inspect a different run." />
                ) : (
                  <EventTimeline events={filteredEvents.slice(-12).reverse()} />
                )}
              </CollapsiblePanel>

              <CollapsiblePanel
                title="Fleet roster"
                description="See who is still searching, who is rotating through base, and who is ready to rejoin coverage."
                defaultOpen={false}
              >
                <div className="space-y-3">
                  {frame.drones.map((drone) => (
                    <div key={drone.id} className="rounded-[20px] border border-border/70 bg-surfaceAlt/55 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-white">Drone {drone.id}</p>
                          <p className="mt-1 text-sm text-muted">{drone.operator_status ?? "Status unavailable"}</p>
                        </div>
                        <span className="pill whitespace-nowrap">{drone.reserve_status_label ?? "Reserve stable"}</span>
                      </div>
                      <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-white/10">
                        <div
                          className={`h-full rounded-full transition-all ${batteryBarClass(drone.battery_pct ?? drone.battery)}`}
                          style={{
                            width: `${Math.max(0, Math.min(100, Number(drone.battery_pct ?? drone.battery ?? 0)))}%`,
                          }}
                        />
                      </div>
                      <div className="mt-3 grid gap-2 text-sm text-white/90 md:grid-cols-2">
                        <span>Battery: {formatBatteryPercent(drone.battery_pct ?? drone.battery)}</span>
                        <span>{serviceEtaLabel(drone)}</span>
                      </div>
                      {drone.assigned_contact_id ? (
                        <p className="mt-3 text-sm leading-6 text-muted">Assigned contact: {drone.assigned_contact_id}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              </CollapsiblePanel>

              <CollapsiblePanel
                title="Contact details"
                description="Open the current possible or confirmed contacts at this step."
                defaultOpen={false}
              >
                {candidateContacts.length > 0 ? (
                  <div className="space-y-2">
                    {candidateContacts.slice(0, 4).map((contact) => (
                      <div key={contact.id} className="rounded-[16px] border border-border/70 bg-surfaceAlt/55 px-4 py-3">
                        <p className="text-sm font-medium text-white">{contact.status_label ?? "Possible Contact"}</p>
                        <p className="mt-1 text-sm text-muted">{contact.note ?? "No contact note recorded."}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm leading-6 text-muted">No candidate contacts are active at this replay step.</p>
                )}
              </CollapsiblePanel>

              <CollapsiblePanel
                title="Technical details"
                description="Open the raw frame metrics behind this replay step."
                defaultOpen={false}
              >
                <pre className="whitespace-pre-wrap text-xs leading-6 text-muted">
                  {JSON.stringify(frame.metrics, null, 2)}
                </pre>
              </CollapsiblePanel>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
