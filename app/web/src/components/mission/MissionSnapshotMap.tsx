import { useEffect, useMemo, useRef, useState } from "react";

import type { Snapshot } from "@/api/types";
import { lifecycleStateLabel } from "@/lib/lifecycle";

const terrainColors = ["#162338", "#1d4d3a", "#4b5563", "#334155", "#274c77"];
const terrainLegendItems = [
  { label: "Plain", color: terrainColors[0] },
  { label: "Forest", color: terrainColors[1] },
  { label: "Hill", color: terrainColors[2] },
  { label: "Urban", color: terrainColors[3] },
  { label: "Water", color: terrainColors[4] },
];
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
    const missionArea = snapshot.mission_area;

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

    const aoiOutline = missionArea?.aoi_outline_grid ?? [];
    if (
      aoiOutline.length > 1 &&
      typeof ctx.moveTo === "function" &&
      typeof ctx.lineTo === "function"
    ) {
      const canRestore = typeof ctx.save === "function" && typeof ctx.restore === "function";
      if (canRestore) {
        ctx.save();
      }
      ctx.strokeStyle = "rgba(241, 245, 249, 0.9)";
      ctx.lineWidth = Math.max(1.25, cellSize * 0.08);
      if (typeof ctx.setLineDash === "function") {
        ctx.setLineDash([Math.max(4, cellSize * 0.35), Math.max(3, cellSize * 0.22)]);
      }
      ctx.beginPath();
      aoiOutline.forEach(([x, y], index) => {
        const px = x * cellSize + cellSize / 2;
        const py = y * cellSize + cellSize / 2;
        if (index === 0) {
          ctx.moveTo(px, py);
        } else {
          ctx.lineTo(px, py);
        }
      });
      if (typeof ctx.stroke === "function") {
        ctx.stroke();
      }
      if (canRestore) {
        ctx.restore();
      }
    }

    snapshot.drones.forEach((drone, index) => {
      const [x, y] = drone.position;
      const centerX = x * cellSize + cellSize / 2;
      const centerY = y * cellSize + cellSize / 2;
      const markerRadius = Math.max(2.5, cellSize * 0.18);
      ctx.fillStyle =
        droneColors[String(drone.lifecycle_state ?? "")] ??
        ["#38bdf8", "#34d399", "#f59e0b", "#f87171", "#a78bfa"][index % 5];
      ctx.beginPath();
      ctx.arc(centerX, centerY, markerRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.lineWidth = Math.max(1, cellSize * 0.06);
      ctx.strokeStyle = "rgba(7, 12, 22, 0.9)";
      if (typeof ctx.stroke === "function") {
        ctx.stroke();
      }
    });

    (snapshot.candidate_contacts ?? []).forEach((contact) => {
      const [x, y] = contact.position;
      const accent =
        contact.status === "contact_confirmed"
          ? "#22c55e"
          : contact.status === "false_alarm_rejected"
            ? "#94a3b8"
            : contact.status === "inspecting_contact" || contact.status === "confirmation_pending"
              ? "#f97316"
              : "#facc15";
      const centerX = x * cellSize + cellSize / 2;
      const centerY = y * cellSize + cellSize / 2;
      const ringRadius = Math.max(3.5, cellSize * 0.24);
      ctx.strokeStyle = accent;
      ctx.lineWidth = Math.max(2, cellSize / 8);
      ctx.beginPath();
      ctx.arc(centerX, centerY, ringRadius, 0, Math.PI * 2);
      if (typeof ctx.stroke === "function") {
        ctx.stroke();
      }
      ctx.fillStyle = accent;
      ctx.beginPath();
      ctx.arc(centerX, centerY, Math.max(1.5, cellSize * 0.08), 0, Math.PI * 2);
      ctx.fill();
    });

    const lastKnown = missionArea?.last_known_grid_position;
    if (
      lastKnown &&
      typeof ctx.moveTo === "function" &&
      typeof ctx.lineTo === "function"
    ) {
      const [x, y] = lastKnown;
      const centerX = x * cellSize + cellSize / 2;
      const centerY = y * cellSize + cellSize / 2;
      const crossRadius = Math.max(4, cellSize * 0.22);
      const canRestore = typeof ctx.save === "function" && typeof ctx.restore === "function";
      if (canRestore) {
        ctx.save();
      }
      ctx.strokeStyle = "#fde68a";
      ctx.lineWidth = Math.max(1.2, cellSize * 0.07);
      ctx.beginPath();
      ctx.moveTo(centerX - crossRadius, centerY);
      ctx.lineTo(centerX + crossRadius, centerY);
      ctx.moveTo(centerX, centerY - crossRadius);
      ctx.lineTo(centerX, centerY + crossRadius);
      if (typeof ctx.stroke === "function") {
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.arc(centerX, centerY, Math.max(3, cellSize * 0.18), 0, Math.PI * 2);
      if (typeof ctx.stroke === "function") {
        ctx.stroke();
      }
      if (canRestore) {
        ctx.restore();
      }
    }

    const [targetX, targetY] = snapshot.target_position;
    ctx.fillStyle = snapshot.target_detected ? "#f97316" : "#facc15";
    ctx.beginPath();
    ctx.arc(
      targetX * cellSize + cellSize / 2,
      targetY * cellSize + cellSize / 2,
      Math.max(2.5, cellSize * 0.16),
      0,
      Math.PI * 2,
    );
    ctx.fill();
    ctx.lineWidth = Math.max(1, cellSize * 0.06);
    ctx.strokeStyle = "rgba(7, 12, 22, 0.9)";
    if (typeof ctx.stroke === "function") {
      ctx.stroke();
    }

    const [baseX, baseY] = snapshot.base_position;
    ctx.fillStyle = "#34d399";
    const baseSize = Math.max(6, cellSize * 0.44);
    ctx.fillRect(
      baseX * cellSize + cellSize / 2 - baseSize / 2,
      baseY * cellSize + cellSize / 2 - baseSize / 2,
      baseSize,
      baseSize,
    );
    ctx.lineWidth = Math.max(1, cellSize * 0.06);
    ctx.strokeStyle = "rgba(7, 12, 22, 0.9)";
    ctx.strokeRect(
      baseX * cellSize + cellSize / 2 - baseSize / 2,
      baseY * cellSize + cellSize / 2 - baseSize / 2,
      baseSize,
      baseSize,
    );
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
      <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-muted">
        <span className="font-medium text-white/80">Terrain legend</span>
        {terrainLegendItems.map((item) => (
          <span key={item.label} className="inline-flex items-center gap-2 rounded-full border border-white/10 px-2.5 py-1">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
              aria-hidden="true"
            />
            {item.label}
          </span>
        ))}
        <span className="inline-flex items-center gap-2 rounded-full border border-white/10 px-2.5 py-1">
          <span className="h-2.5 w-2.5 rounded-full bg-sky-400/70" aria-hidden="true" />
          Belief overlay
        </span>
        <span className="inline-flex items-center gap-2 rounded-full border border-white/10 px-2.5 py-1">
          <span className="h-2.5 w-2.5 rounded-full bg-slate-950" aria-hidden="true" />
          Blocked / no-go
        </span>
      </div>
      <p className="mt-2 text-[11px] text-muted">
        Grid colors show terrain categories rather than elevation. A dashed outline marks the selected AOI, the green
        square marks base, and the amber cross marks the last known point when one is set.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {snapshot.search_pattern_label ? (
          <span className="pill whitespace-nowrap">
            {snapshot.search_pattern_label}
            {snapshot.search_pattern_rebalanced ? " | Rebalanced" : ""}
          </span>
        ) : null}
        {snapshot.mission_area?.location_display_name ? (
          <span className="pill whitespace-nowrap">
            {snapshot.mission_area.location_display_name}
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
