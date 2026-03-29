import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { useRuns } from "@/api/hooks";
import type { Snapshot } from "@/api/types";
import { EventTimeline } from "@/components/mission/EventTimeline";
import { MissionSnapshotMap } from "@/components/mission/MissionSnapshotMap";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
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

  useEffect(() => {
    if (!runId && completedRuns[0]) {
      setRunId(completedRuns[0].id);
    }
  }, [completedRuns, runId]);

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
  const frame = frames[Math.min(frameIndex, Math.max(frames.length - 1, 0))];
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
    <div className="space-y-6">
      <Panel title="Replay Selection" description="Load a completed run and scrub through mission evolution step by step.">
        <div className="grid gap-4 md:grid-cols-[1.4fr_0.7fr_0.7fr]">
          <label className="space-y-2 text-sm text-muted">
            <span>Completed run</span>
            <select
              className="w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-white"
              value={runId}
              onChange={(event) => {
                setRunId(event.target.value);
                setFrameIndex(0);
              }}
            >
              {completedRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.id}
                </option>
              ))}
            </select>
          </label>
          <div className="rounded-2xl border border-border bg-surfaceAlt/70 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">Status</p>
            <div className="mt-2">
              <StatusBadge status={selectedRun?.status ?? "completed"} />
            </div>
          </div>
          <div className="rounded-2xl border border-border bg-surfaceAlt/70 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">Completed</p>
            <p className="mt-2 text-sm text-white">
              {selectedRun?.completed_at ? formatTimestamp(selectedRun.completed_at) : "n/a"}
            </p>
          </div>
        </div>
      </Panel>

      {!frame ? (
        <EmptyState title="Replay is still building" body="This run does not have replay frames available yet." />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.9fr]">
          <Panel title="Mission Replay" description="Belief state, drones, obstacles, and target estimate at the selected frame.">
            <MissionSnapshotMap snapshot={frame} />
            <div className="mt-5 space-y-3">
              <div className="flex items-center justify-between text-sm text-muted">
                <span>
                  Frame {frameIndex + 1} of {frames.length}
                </span>
                <span>Step {frame.step}</span>
              </div>
              <input
                type="range"
                min={0}
                max={Math.max(frames.length - 1, 0)}
                value={Math.min(frameIndex, Math.max(frames.length - 1, 0))}
                onChange={(event) => setFrameIndex(Number(event.target.value))}
                className="w-full accent-sky-400"
              />
            </div>
          </Panel>

          <Panel title="Event Timeline" description="Events accumulated up to the current replay frame.">
            {filteredEvents.length === 0 ? (
              <EmptyState title="No events at this point" body="Move later in the timeline or inspect a different run." />
            ) : (
              <EventTimeline events={filteredEvents.slice(-12).reverse()} />
            )}
          </Panel>
        </div>
      )}

      {frame && (
        <Panel title="Frame Details" description="Structured snapshot data for detailed inspection and debugging.">
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-2xl border border-border bg-surfaceAlt/70 p-4 text-xs text-muted">
            {JSON.stringify(frame.metrics, null, 2)}
          </pre>
        </Panel>
      )}
    </div>
  );
}
