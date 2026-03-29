import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useRuns } from "@/api/hooks";
import type { Snapshot } from "@/api/types";
import { EventTimeline } from "@/components/mission/EventTimeline";
import { MissionSnapshotMap } from "@/components/mission/MissionSnapshotMap";
import { DetailPanel } from "@/components/ui/DetailPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Panel } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
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

  const filteredEvents = (eventsQuery.data?.events ?? []).filter(
    (event) => Number(event.step ?? 0) <= Number(frame?.step ?? 0),
  );
  const selectedRun = completedRuns.find((run) => run.id === runId);

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
            <MetricCard label="Step" value={frame.step} emphasis="accent" />
            <MetricCard label="Weather" value={frame.weather} />
            <MetricCard label="Detection" value={frame.target_detected ? "Confirmed" : "Searching"} />
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.22fr_0.92fr]">
            <Panel
              eyebrow="Playback"
              title="Mission replay"
              description="Replay the spatial state, then correlate it with the timeline and event stream."
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
              </div>
            </Panel>

            <div className="space-y-6">
              <DetailPanel
                title="Selected step"
                items={[
                  { label: "Step", value: frame.step },
                  { label: "Strategy", value: frame.strategy },
                  { label: "Coordination", value: frame.coordination_mode },
                  { label: "Visited cells", value: frame.visited_cells.length },
                  { label: "Searched cells", value: frame.searched_cells.length },
                ]}
              />
              <Panel
                eyebrow="Event stream"
                title="Events at or before this frame"
                description="Use the event feed to understand what changed and why that moment matters."
              >
                {filteredEvents.length === 0 ? (
                  <EmptyState title="No events at this point" body="Move later in the timeline or inspect a different run." />
                ) : (
                  <EventTimeline events={filteredEvents.slice(-12).reverse()} />
                )}
              </Panel>
            </div>
          </div>

          <Panel
            eyebrow="Metrics"
            title="Selected frame summary"
            description="This view is useful for explaining what the replay frame implies operationally."
          >
            <pre className="whitespace-pre-wrap text-xs leading-6 text-muted">{JSON.stringify(frame.metrics, null, 2)}</pre>
          </Panel>
        </>
      )}
    </div>
  );
}
