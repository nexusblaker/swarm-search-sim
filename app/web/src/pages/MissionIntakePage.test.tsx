import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { MissionIntakePage } from "@/pages/MissionIntakePage";

vi.mock("@/api/hooks", () => ({
  useInvalidateResources: () => vi.fn(),
}));

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<object>("@tanstack/react-query");
  return {
    ...actual,
    useMutation: () => ({
      mutate: vi.fn(),
      data: undefined,
      isPending: false,
      reset: vi.fn(),
    }),
  };
});

describe("MissionIntakePage", () => {
  it("renders the staged intake flow and supports mixed fleet editing", () => {
    render(
      <MemoryRouter>
        <MissionIntakePage />
      </MemoryRouter>,
    );

    expect(screen.getByText("Build a new mission in five guided steps")).toBeInTheDocument();
    expect(screen.getByText("Describe the situation")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /step 2 assets/i }));
    fireEvent.click(screen.getByRole("button", { name: /mixed fleet/i }));

    expect(screen.getByText("Add another drone type")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Add another drone type"));

    expect(screen.getByText("Drone type 3")).toBeInTheDocument();
  });
});
