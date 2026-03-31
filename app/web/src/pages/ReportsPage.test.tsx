import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReportsPage } from "@/pages/ReportsPage";

vi.mock("@/api/hooks", () => ({
  useReports: () => ({
    data: {
      items: [
        {
          id: "report-1",
          owner_type: "review",
          owner_id: "review-1",
          report_type: "review_report",
          created_at: 1_700_000_000,
          summary_json: {
            status: "ready",
            sensing_lifecycle: {
              operator_summary: "Possible contacts were detected and tracked for closer inspection.",
            },
          },
          file_path: "C:/tmp/report.html",
          run_id: "run-1",
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
}));

describe("ReportsPage", () => {
  it("shows indexed reports and selected report details", () => {
    render(<ReportsPage />);

    expect(screen.getByText("Indexed reports")).toBeInTheDocument();
    expect(screen.getAllByText("After-action report").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/review:review-1/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Export after-action report")).toBeInTheDocument();
    expect(screen.getByText("Sensing workflow")).toBeInTheDocument();
  });
});
