import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RecommendationCard } from "@/components/ui/RecommendationCard";

describe("RecommendationCard", () => {
  it("renders the recommendation briefing fields", () => {
    render(
      <RecommendationCard
        strategy="information_gain"
        drones={4}
        reserveThreshold={28}
        explanation="This setup balances expected success and search speed."
        riskSummary={{ battery: "moderate" }}
        uncertaintySummary={{ confidence: 0.78 }}
      />,
    );

    expect(screen.getByText("Recommended setup")).toBeInTheDocument();
    expect(screen.getByText("information_gain")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("28%")).toBeInTheDocument();
    expect(screen.getByText(/balances expected success/i)).toBeInTheDocument();
  });
});
