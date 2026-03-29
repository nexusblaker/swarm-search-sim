import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressBar } from "@/components/ui/ProgressBar";

describe("ProgressBar", () => {
  it("accepts fractional values", () => {
    const { getByRole, getByTestId } = render(<ProgressBar value={0.42} />);
    expect(getByRole("progressbar")).toHaveAttribute("aria-valuenow", "42");
    expect((getByTestId("progress-fill") as HTMLDivElement).style.width).toBe("42%");
  });

  it("accepts percentage values", () => {
    const { getByRole, getByTestId } = render(<ProgressBar value={42} />);
    expect(getByRole("progressbar")).toHaveAttribute("aria-valuenow", "42");
    expect((getByTestId("progress-fill") as HTMLDivElement).style.width).toBe("42%");
  });
});
