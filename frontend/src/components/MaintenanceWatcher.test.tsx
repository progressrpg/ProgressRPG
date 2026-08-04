import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import MaintenanceWatcher from "./MaintenanceWatcher";
import { MaintenanceProvider, useMaintenanceContext } from "../context/MaintenanceContext";
import * as api from "../utils/api";

function ActiveMaintenanceProbe() {
  const { maintenance } = useMaintenanceContext();
  return <span data-testid="maintenance-active">{String(maintenance.active)}</span>;
}

describe("MaintenanceWatcher", () => {
  afterEach(() => {
    api.setMaintenanceHandler(null);
    api.setNetworkErrorHandler(null);
    vi.restoreAllMocks();
  });

  it("registers apiFetch's maintenance/network handlers on mount and clears them on unmount", () => {
    const setMaintenanceHandlerSpy = vi.spyOn(api, "setMaintenanceHandler");
    const setNetworkErrorHandlerSpy = vi.spyOn(api, "setNetworkErrorHandler");

    const { unmount } = render(
      <MemoryRouter>
        <MaintenanceProvider>
          <MaintenanceWatcher />
        </MaintenanceProvider>
      </MemoryRouter>
    );

    expect(setMaintenanceHandlerSpy).toHaveBeenCalledWith(expect.any(Function));
    expect(setNetworkErrorHandlerSpy).toHaveBeenCalledWith(expect.any(Function));

    unmount();

    expect(setMaintenanceHandlerSpy).toHaveBeenLastCalledWith(null);
    expect(setNetworkErrorHandlerSpy).toHaveBeenLastCalledWith(null);
  });

  it("flips maintenance.active when apiFetch hits a 503, without apiFetch touching window directly", async () => {
    globalThis.fetch = () => Promise.resolve({ ok: false, status: 503 } as Response);

    render(
      <MemoryRouter>
        <MaintenanceProvider>
          <MaintenanceWatcher />
          <ActiveMaintenanceProbe />
        </MaintenanceProvider>
      </MemoryRouter>
    );

    const probe = () => document.querySelector('[data-testid="maintenance-active"]');
    expect(probe()?.textContent).toBe("false");

    await act(async () => {
      await expect(api.apiFetch("/me/", {}, "test-token")).rejects.toMatchObject({
        kind: "service_unavailable",
      });
    });

    expect(probe()?.textContent).toBe("true");
  });
});
