import { describe, expect, it } from "vitest";

import { formatTimestamp, safeString } from "@/lib/format";

describe("format helpers", () => {
  it("returns n/a for missing timestamps", () => {
    expect(formatTimestamp(undefined)).toBe("n/a");
  });

  it("formats scalar values safely", () => {
    expect(safeString("alpha")).toBe("alpha");
    expect(safeString(42)).toBe("42");
    expect(safeString(undefined)).toBe("n/a");
  });
});
