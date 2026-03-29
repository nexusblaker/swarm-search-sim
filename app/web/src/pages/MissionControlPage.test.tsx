import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { MissionControlPage } from "@/pages/MissionControlPage";

const snapshot = {
  step: 5,
  done: false,
  paused: false,
  weather: "clear",
  strategy: "information_gain",
  coordination_mode: "centralized",
  base_position: [0, 0],
  terrain_grid: [
    [0, 0],
    [0, 0],
  ],
  obstacle_mask: [
    [false, false],
    [false, false],
  ],
  probability_map: [
    [0.25, 0.25],
    [0.25, 0.25],
  ],
  target_position: [1, 1],
  target_detected: false,
  visited_cells: [],
  searched_cells: [],
  last_searched_cells: [],
  communication_links: [],
  reserved_paths: {},
  global_objectives: {},
  drones: [
    {
      id: 0,
      position: [0, 0],
      battery: 90,
      path_history: [[0, 0]],
      planned_path: [],
      comms_online: true,
      returning_to_base: false,
      stale_steps: 0,
    },
  ],
  metrics: {},
};

vi.mock("@/api/hooks", () => ({
  useRuns: () => ({
    data: {
      items: [
        {
          id: "run-1",
          scenario_id: "scenario-1",
          plan_id: "plan-1",
          status: "running",
          created_at: 1_700_000_000,
          updated_at: 1_700_000_001,
          config_json: {},
          summary_json: { strategy: "information_gain", scenario_family: "mixed_terrain" },
          latest_snapshot_json: snapshot,
          output_dir: "C:/tmp",
          artifact_paths: {},
          job: { progress: 0.54 },
          interventions: [],
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
  usePlans: () => ({ data: { items: [{ id: "plan-1", name: "Plan One" }] } }),
  useScenarios: () => ({ data: { items: [{ id: "scenario-1", name: "Scenario One" }] } }),
  useComparisons: () => ({ data: { items: [] } }),
  useLibraryTemplates: () => ({ data: { items: [] } }),
}));

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<object>("@tanstack/react-query");
  return {
    ...actual,
    useQuery: ({ queryKey }: { queryKey: string[] }) => {
      if (queryKey[0] === "replay") {
        return { data: { replay: [snapshot] }, isLoading: false, error: null };
      }
      if (queryKey[0] === "events") {
        return { data: { events: [{ event_type: "scan", step: 5 }] }, isLoading: false, error: null };
      }
      return { data: undefined, isLoading: false, error: null };
    },
    useMutation: () => ({ mutate: vi.fn(), error: null }),
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

describe("MissionControlPage", () => {
  it("renders the live monitoring workspace for an active run", () => {
    render(
      <MemoryRouter>
        <MissionControlPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Mission control")).toBeInTheDocument();
    expect(screen.getByText("Monitoring run-1")).toBeInTheDocument();
    expect(screen.getByText("What changed recently")).toBeInTheDocument();
    expect(screen.getByText("Launch mission run")).toBeInTheDocument();
  });
});
