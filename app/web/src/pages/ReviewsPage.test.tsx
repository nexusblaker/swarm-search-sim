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
            mission_timeline: "Generated from replay, events, and intervention history.",
            actual_outcome: { status: "completed", metrics: { mission_success: true } },
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
          },
          timeline_json: {
            key_events: [
              {
                event_type: "battery_return_ordered",
                step: 3,
                summary: "Drone 0 returned to base to protect reserve margin.",
              },
            ],
          },
          alternate_plan_json: { summary: "An alternate plan would have traded coverage speed for reserve." },
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
  it("shows lifecycle-aware after-action review content", () => {
    render(<ReviewsPage />);

    expect(screen.getByText("After-action review")).toBeInTheDocument();
    expect(screen.getByText("Battery rotation summary")).toBeInTheDocument();
    expect(screen.getByText("Review timeline")).toBeInTheDocument();
    expect(screen.getByText("Open review report")).toBeInTheDocument();
  });
});
