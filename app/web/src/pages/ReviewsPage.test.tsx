import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReviewsPage } from "@/pages/ReviewsPage";

vi.mock("@/api/hooks", () => ({
  useReviews: () => ({
    data: {
      items: [
        {
          id: "review-1",
          run_id: "run-1",
          plan_id: "plan-1",
          comparison_id: "comparison-1",
          name: "After Action Review run-1",
          created_at: 1_700_000_000,
          updated_at: 1_700_000_001,
          summary_json: {
            mission_timeline: "The fleet established coverage, inspected two contacts, and completed the run without losing mission continuity.",
            actual_outcome: { status: "completed", metrics: { mission_success: true } },
            deviation_summary:
              "The run differed materially from the original recommendation in search strategy and reserve policy.",
            deviation_from_recommendation: {
              strategy_differs: true,
              drone_count_differs: false,
              coordination_differs: false,
              reserve_differs: true,
            },
            mission_area: {
              operator_summary: "Katoomba AOI covers about 14.2 km² across 4.8 by 3.1 km at roughly 400 m cells.",
              area_sq_km: 14.2,
              grid_size: [12, 10],
              environment_summary: { label: "Forested mixed terrain" },
              weather_summary: { condition_label: "Clear with light wind" },
              terrain_summary: {
                operator_summary: "The selected area is mostly forest, with elevated slope burden and workable trail access.",
              },
            },
            battery_lifecycle: {
              reserve_preset: "balanced",
              asset_utilization_summary: "2 return-to-base cycle(s) were recorded.",
              mission_continuity_impact: "Coverage stayed mostly stable during asset rotation.",
              battery_margin_summary: { sustainability: "Battery margins remained healthy for sustained coverage." },
              return_to_base_count: 2,
              recharge_completed_count: 2,
              redeploy_count: 2,
              coverage_gap_count: 1,
            },
            sensing_lifecycle: {
              operator_summary: "The team investigated possible contacts and rejected false alarms before resuming the search.",
              inspection_burden_summary: "A limited number of inspection passes were needed to resolve possible contacts.",
              mission_impact_summary: "Inspection work remained contained and did not materially disrupt the wider search.",
              candidate_detection_count: 2,
              inspection_initiated_count: 2,
              inspection_pass_count: 2,
              false_positive_count: 1,
            },
            search_pattern: {
              pattern_label: "Broad Area Sweep",
              summary: "Spreads the fleet across evenly spaced lanes to maximize early area coverage.",
              reason: "The last known position was uncertain, so early coverage mattered most.",
              mission_effect_summary: "The mission largely held its planned broad area sweep layout.",
              change_count: 1,
            },
            confidence_summary: {
              confidence_level: "moderate",
              confidence_reason: "Terrain and inspection timing still leave some spread in the operational estimate.",
            },
            feasibility_summary: {
              status: "warning",
              operator_summary: "The mission remained feasible, but rotation pressure required close attention.",
              next_watch: "Coverage may thin if wind rises.",
            },
            assumptions_summary: "Battery, weather, and terrain effects follow the documented calibration baseline.",
            known_limitations_summary: "The model remains a grid-based approximation of field conditions.",
            provenance_manifest: {
              model_version: "v1.8.0",
              scenario_version: "scenario-2026-04",
              calibration_version: "cal-2026-04",
              deployment_mode: "base_launch",
            },
            benchmark_context: ["Benchmarked against the medium steep terrain validation case."],
          },
          timeline_json: {
            key_events: [
              {
                event_type: "false_positive_rejected",
                step: 3,
                summary: "Drone 0 rejected the contact as a false alarm.",
              },
            ],
          },
          alternate_plan_json: { available: true, summary: "An alternate plan would have traded coverage speed for reserve." },
          report_id: "report-1",
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
  useRuns: () => ({
    data: {
      items: [
        {
          id: "run-1",
          status: "completed",
        },
      ],
    },
  }),
  useReports: () => ({
    data: {
      items: [
        {
          id: "report-1",
          owner_type: "review",
          owner_id: "review-1",
          report_type: "after_action_review",
          created_at: 1_700_000_000,
          summary_json: {},
          file_path: "C:/tmp/review.html",
          run_id: "run-1",
        },
      ],
    },
  }),
}));

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<object>("@tanstack/react-query");
  return {
    ...actual,
    useQuery: () => ({ data: { status: "completed" }, isLoading: false, error: null }),
    useMutation: () => ({ mutate: vi.fn(), error: null }),
  };
});

describe("ReviewsPage", () => {
  it("shows an executive summary first and keeps raw comparison detail secondary", () => {
    render(<ReviewsPage />);

    expect(screen.getByText("After-action review")).toBeInTheDocument();
    expect(screen.getByText("Mission outcome")).toBeInTheDocument();
    expect(screen.getByText("Mission area review")).toBeInTheDocument();
    expect(screen.getByText("Search pattern review")).toBeInTheDocument();
    expect(screen.getByText("Deviation from recommendation")).toBeInTheDocument();
    expect(
      screen.getByText(/differed materially from the original recommendation in search strategy and reserve policy/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Technical appendix")).toBeInTheDocument();
    expect(screen.getByText("Structured appendix")).toBeInTheDocument();
    expect(screen.queryByText("Strategy Differs")).not.toBeInTheDocument();
    expect(screen.getByText("Open after-action report")).toBeInTheDocument();
  });
});
