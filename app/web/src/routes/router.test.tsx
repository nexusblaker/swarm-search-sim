import { describe, expect, it } from "vitest";

import { appRouteDefinitions } from "@/routes/router";

describe("app routes", () => {
  it("exposes the operator workflow routes", () => {
    const rootRoute = appRouteDefinitions[0];
    const paths = (rootRoute.children ?? [])
      .map((route) => ("index" in route && route.index ? "/" : "path" in route ? route.path : undefined))
      .filter(Boolean);

    expect(paths).toEqual(
      expect.arrayContaining([
        "/",
        "scenarios",
        "plans",
        "library",
        "comparisons",
        "recommendations",
        "mission-control",
        "replay",
        "runs",
        "experiments",
        "reports",
        "reviews",
      ]),
    );
  });
});
