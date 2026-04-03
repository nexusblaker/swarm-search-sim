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
        confidenceSummary={{
          confidence_level: "moderate",
          confidence_reason: "Results are directionally useful, but terrain and timing spread still matter.",
        }}
        feasibilitySummary={{
          status: "warning",
          status_label: "Warning",
          operator_summary: "Mission is feasible, but the current setup carries operational watch items.",
          next_watch: "Coverage may thin during rotation.",
          warnings: [{ title: "Coverage pressure", summary: "The area is large relative to endurance." }],
        }}
        riskSummary={{ battery: "moderate" }}
        uncertaintySummary={{ confidence: 0.78 }}
        technicalDetails={{
          mission_intent: "high_confidence_confirmation",
          mission_area_summary: "Katoomba AOI covers about 14.2 kmÂ² across 4.8 by 3.1 km at roughly 400 m cells.",
          first_candidate_band: { low: 12, mean: 16, high: 20 },
          confirmed_detection_band: { low: 24, mean: 31, high: 40 },
        }}
      />,
    );

    expect(screen.getByText("Recommended plan")).toBeInTheDocument();
    expect(screen.getByText(/use a focused confirmation search/i)).toBeInTheDocument();
    expect(screen.getAllByText("Broad Area Sweep").length).toBeGreaterThan(0);
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("28%")).toBeInTheDocument();
    expect(screen.getByText(/balances expected success/i)).toBeInTheDocument();
    expect(screen.getByText(/guided from a single mission desk/i)).toBeInTheDocument();
    expect(screen.getByText(/Katoomba AOI covers about 14.2 kmÂ²/i)).toBeInTheDocument();
    expect(screen.getByText("Mission readiness")).toBeInTheDocument();
    expect(screen.getByText("Expected timing")).toBeInTheDocument();
    expect(screen.getByText(/First candidate: 12 to 20 minutes/i)).toBeInTheDocument();
  });
});
