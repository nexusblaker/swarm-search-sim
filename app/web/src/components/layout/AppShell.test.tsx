import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/layout/AppShell";

describe("AppShell", () => {
  it("supports collapsing the sidebar", () => {
    Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: 1600 });
    const getItem = vi.spyOn(Storage.prototype, "getItem").mockReturnValue("false");
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => undefined);

    render(
      <MemoryRouter initialEntries={["/mission-intake"]}>
        <AppShell>
          <div>Test page</div>
        </AppShell>
      </MemoryRouter>,
    );

    const collapseButton = screen.getByRole("button", { name: "Collapse sidebar" });
    fireEvent.click(collapseButton);

    expect(setItem).toHaveBeenCalledWith("swarm-sidebar-collapsed", "true");
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toBeInTheDocument();

    getItem.mockRestore();
    setItem.mockRestore();
  });
});
