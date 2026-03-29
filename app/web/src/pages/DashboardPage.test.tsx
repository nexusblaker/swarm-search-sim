import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { DashboardPage } from "@/pages/DashboardPage";

vi.mock("@/api/hooks", () => ({
  useDashboardSummary: () => ({
    data: {
      counts: { scenarios: 3, plans: 2, comparisons: 1, runs: 4, reviews: 1, reports: 2 },
      active_runs: 1,
      completed_runs: 3,
      queued_jobs: 1,
      backend_status: "ok",
      recent_runs: [
        {
          id: "run-1",
          status: "running",
          plan_id: "plan-1",
          summary_json: { strategy: "information_gain" },
          updated_at: 1_700_000_000,
        },
      ],
      recent_reports: [
        {
          id: "report-1",
          owner_type: "review",
          owner_id: "review-1",
          report_type: "review_report",
          created_at: 1_700_000_000,
        },
      ],
      recent_activity: [
        {
          id: "run-1",
          kind: "run",
          title: "Run run-1",
          subtitle: "information_gain · plan-1",
          timestamp: 1_700_000_000,
          status: "running",
        },
      ],
      suggested_actions: [
        {
          label: "Create mission plan",
          description: "Start from a template.",
          route: "/plans",
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
}));

describe("DashboardPage", () => {
  it("renders summary counts and suggested actions", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Mission planning at a glance")).toBeInTheDocument();
    expect(screen.getAllByText("Create mission plan").length).toBeGreaterThan(0);
    expect(screen.getByText("What changed most recently")).toBeInTheDocument();
    expect(screen.getByText("Run run-1")).toBeInTheDocument();
  });
});
