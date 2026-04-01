import { useEffect, useMemo, useRef, useState } from "react";

import type { Snapshot } from "@/api/types";
import { lifecycleStateLabel } from "@/lib/lifecycle";

const terrainColors = ["#162338", "#1d4d3a", "#4b5563", "#334155", "#274c77"];
const droneColors: Record<string, string> = {
  searching: "#38bdf8",
  deploying: "#38bdf8",
  redeploying: "#2dd4bf",
  returning_to_base: "#f59e0b",
  recharging_or_swapping: "#94a3b8",
  ready_to_redeploy: "#34d399",
  unavailable: "#f87171",
};

export function MissionSnapshotMap({ snapshot }: { snapshot: Snapshot }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [canvasUnavailable, setCanvasUnavailable] = useState(false);
  const dimensions = useMemo(() => {
    const height = snapshot.terrain_grid.length;
    const width = snapshot.terrain_grid[0]?.length ?? 0;
    return { width, height };
  }, [snapshot]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || dimensions.width === 0 || dimensions.height === 0) {
      return;
    }
    let ctx: CanvasRenderingContext2D | null = null;
    try {
      ctx = canvas.getContext("2d");
    } catch {
      setCanvasUnavailable(true);
      return;
    }
    if (!ctx) {
      setCanvasUnavailable(true);
      return;
    }
    setCanvasUnavailable(false);
    const cellSize = Math.max(12, Math.floor(560 / Math.max(dimensions.width, dimensions.height)));
    canvas.width = dimensions.width * cellSize;
    canvas.height = dimensions.height * cellSize;

    for (let y = 0; y < dimensions.height; y += 1) {
      for (let x = 0; x < dimensions.width; x += 1) {
        const terrain = snapshot.terrain_grid[y]?.[x] ?? 0;
        ctx.fillStyle = terrainColors[terrain] ?? "#1e293b";
        ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
        const belief = snapshot.probability_map[y]?.[x] ?? 0;
        if (belief > 0) {
          ctx.fillStyle = `rgba(56, 189, 248, ${Math.min(0.7, belief * 30)})`;
          ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
        }
        if (snapshot.obstacle_mask[y]?.[x]) {
          ctx.fillStyle = "rgba(12, 18, 32, 0.88)";
          ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
        }
        ctx.strokeStyle = "rgba(255,255,255,0.03)";
        ctx.strokeRect(x * cellSize, y * cellSize, cellSize, cellSize);
      }
    }

    snapshot.drones.forEach((drone, index) => {
      const [x, y] = drone.position;
      ctx.fillStyle =
        droneColors[String(drone.lifecycle_state ?? "")] ??
        ["#38bdf8", "#34d399", "#f59e0b", "#f87171", "#a78bfa"][index % 5];
      ctx.beginPath();
      ctx.arc(
        x * cellSize + cellSize / 2,
        y * cellSize + cellSize / 2,
        Math.max(4, cellSize / 3),
        0,
        Math.PI * 2,
      );
      ctx.fill();
    });

    (snapshot.candidate_contacts ?? []).forEach((contact) => {
      const [x, y] = contact.position;
      ctx.strokeStyle =
        contact.status === "contact_confirmed"
          ? "#22c55e"
          : contact.status === "false_alarm_rejected"
            ? "#94a3b8"
            : contact.status === "inspecting_contact" || contact.status === "confirmation_pending"
              ? "#f97316"
              : "#facc15";
      ctx.lineWidth = Math.max(2, cellSize / 8);
      ctx.beginPath();
      ctx.arc(
        x * cellSize + cellSize / 2,
        y * cellSize + cellSize / 2,
        Math.max(5, cellSize / 2.5),
        0,
        Math.PI * 2,
      );
      if (typeof ctx.stroke === "function") {
        ctx.stroke();
      }
    });

    const [targetX, targetY] = snapshot.target_position;
    ctx.fillStyle = snapshot.target_detected ? "#f97316" : "#facc15";
    ctx.beginPath();
    ctx.arc(
      targetX * cellSize + cellSize / 2,
      targetY * cellSize + cellSize / 2,
      Math.max(3, cellSize / 4),
      0,
      Math.PI * 2,
    );
    ctx.fill();
  }, [dimensions, snapshot]);

  return (
    <div className="overflow-hidden rounded-3xl border border-border bg-[#09111c] p-3">
      {canvasUnavailable ? (
        <div className="flex min-h-[280px] items-center justify-center rounded-2xl border border-dashed border-border bg-surface/70 px-6 text-center text-sm text-muted">
          Live mission map preview is unavailable in this environment. Replay images and mission metrics remain
          available for review.
        </div>
      ) : (
        <canvas ref={canvasRef} className="max-w-full rounded-2xl" />
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {snapshot.search_pattern_label ? (
          <span className="pill whitespace-nowrap">
            {snapshot.search_pattern_label}
            {snapshot.search_pattern_rebalanced ? " | Rebalanced" : ""}
          </span>
        ) : null}
        {snapshot.drones.map((drone) => (
          <span key={drone.id} className="pill whitespace-nowrap">
            Drone {drone.id} | {drone.operator_status ?? lifecycleStateLabel(drone.lifecycle_state)}
          </span>
        ))}
        {(snapshot.candidate_contacts ?? []).slice(0, 4).map((contact) => (
          <span key={contact.id} className="pill whitespace-nowrap">
            {contact.status_label ?? "Possible Contact"} | {Math.round(Number(contact.confidence ?? 0) * 100)}%
          </span>
        ))}
      </div>
    </div>
  );
}
