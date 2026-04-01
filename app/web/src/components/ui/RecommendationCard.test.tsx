import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RecommendationCard } from "@/components/ui/RecommendationCard";

describe("RecommendationCard", () => {
  it("renders the recommendation briefing fields", () => {
    render(
      <RecommendationCard
        strategy="information_gain"
        searchPattern="broad_area_sweep"
        searchPatternLabel="Broad Area Sweep"
        searchPatternSummary="Spreads the fleet across evenly spaced lanes to maximize early area coverage."
        searchPatternReason="The last known position is uncertain and the search area is wide."
        searchPatternFitSummary="Best when the location is uncertain and early coverage matters most."
        drones={4}
        reserveThreshold={28}
        explanation="This setup balances expected success and search speed."
        conciseSummary="Recommended: use a focused confirmation search with 4 drones from the southern base."
        topAlternativeSummary="Alternative: a broad sweep with 5 drones."
        keyTradeoffs={["Holds more battery margin than the top alternative."]}
        keyRisks={["Coverage speed may lag the requested search tempo."]}
        teamCoordinationLabel="guided from a single mission desk"
        riskSummary={{ battery: "moderate" }}
        uncertaintySummary={{ confidence: 0.78 }}
        technicalDetails={{ mission_intent: "high_confidence_confirmation" }}
      />,
    );

    expect(screen.getByText("Recommended plan")).toBeInTheDocument();
    expect(screen.getByText(/use a focused confirmation search/i)).toBeInTheDocument();
    expect(screen.getAllByText("Broad Area Sweep").length).toBeGreaterThan(0);
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("28%")).toBeInTheDocument();
    expect(screen.getByText(/balances expected success/i)).toBeInTheDocument();
    expect(screen.getByText(/guided from a single mission desk/i)).toBeInTheDocument();
  });
});
