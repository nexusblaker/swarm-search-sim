import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReplayPage } from "@/pages/ReplayPage";

const snapshot = {
  step: 4,
  done: false,
  paused: false,
  weather: "clear",
  strategy: "information_gain",
  coordination_mode: "centralized",
  run_phase: "Battery rotation underway",
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
  active_search_drones: [0],
  lifecycle_summary: {
    run_phase: "Battery rotation underway",
    returning_drones: 1,
    recharging_drones: 0,
    active_search_drones: 1,
    coverage_gap_active: true,
  },
  sensing_summary: {
    active_candidate_contacts: 1,
    contacts_under_inspection: 1,
    operator_summary: "A possible contact is being inspected.",
  },
  candidate_contacts: [
    {
      id: "contact-1",
      position: [1, 1],
      status: "inspecting_contact",
      status_label: "Inspecting Contact",
      confidence: 0.61,
      note: "Inspection pass underway.",
    },
  ],
  drones: [
    {
      id: 0,
      position: [0, 0],
      battery: 68,
      battery_pct: 68,
      path_history: [[0, 0]],
      planned_path: [],
      comms_online: true,
      returning_to_base: true,
      stale_steps: 0,
      lifecycle_state: "returning_to_base",
      operator_status: "Returning to Base",
      reserve_status_label: "Returning Now",
      return_service_eta_steps: 4,
      assigned_contact_id: "contact-1",
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
          status: "completed",
          created_at: 1_700_000_000,
          updated_at: 1_700_000_001,
          completed_at: 1_700_000_002,
          config_json: {},
          summary_json: { run_phase: "Battery rotation underway" },
          latest_snapshot_json: snapshot,
          output_dir: "C:/tmp",
          artifact_paths: {},
          interventions: [],
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
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
        return {
          data: {
            events: [
              {
                event_type: "inspection_initiated",
                step: 4,
                summary: "Drone 0 moved to inspect the possible contact.",
              },
            ],
          },
          isLoading: false,
          error: null,
        };
      }
      return { data: undefined, isLoading: false, error: null };
    },
  };
});

describe("ReplayPage", () => {
  it("shows lifecycle-aware replay details", () => {
    render(<ReplayPage />);

    expect(screen.getByText("Mission replay")).toBeInTheDocument();
    expect(screen.getByText("Fleet roster")).toBeInTheDocument();
    expect(screen.getByText(/Step 4 \| Inspection Started/i)).toBeInTheDocument();
    expect(screen.getByText("Frame summary")).toBeInTheDocument();
  });
});
