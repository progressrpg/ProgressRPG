import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MaintenanceProvider, useMaintenanceContext } from "./MaintenanceContext";

function Consumer() {
  const { maintenance, setMaintenance } = useMaintenanceContext();
  return (
    <div>
      <span data-testid="active">{String(maintenance.active)}</span>
      <span data-testid="details">{maintenance.details?.name ?? "none"}</span>
      <button
        onClick={() =>
          setMaintenance({
            active: true,
            details: { name: "Scheduled downtime" },
          })
        }
      >
        trigger
      </button>
    </div>
  );
}

describe("MaintenanceProvider", () => {
  it("provides the default (inactive) maintenance state", () => {
    render(
      <MaintenanceProvider>
        <Consumer />
      </MaintenanceProvider>
    );

    expect(screen.getByTestId("active")).toHaveTextContent("false");
    expect(screen.getByTestId("details")).toHaveTextContent("none");
  });

  it("updates the maintenance state via setMaintenance", () => {
    render(
      <MaintenanceProvider>
        <Consumer />
      </MaintenanceProvider>
    );

    act(() => {
      screen.getByText("trigger").click();
    });

    expect(screen.getByTestId("active")).toHaveTextContent("true");
    expect(screen.getByTestId("details")).toHaveTextContent("Scheduled downtime");
  });
});

describe("useMaintenanceContext", () => {
  it("throws when used outside a MaintenanceProvider", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    function BareConsumer() {
      useMaintenanceContext();
      return null;
    }

    expect(() => render(<BareConsumer />)).toThrow(
      "useMaintenanceContext must be used within a MaintenanceProvider"
    );

    consoleErrorSpy.mockRestore();
  });
});
