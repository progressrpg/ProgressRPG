import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useMaintenanceStatus } from "./useMaintenanceStatus";

const mockUseMaintenanceContext = vi.fn();
const mockApiFetch = vi.fn();

vi.mock("../context/MaintenanceContext", () => ({
  useMaintenanceContext: () => mockUseMaintenanceContext(),
}));

vi.mock("../utils/api", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

describe("useMaintenanceStatus", () => {
  const setMaintenance = vi.fn();

  beforeEach(() => {
    mockApiFetch.mockReset();
    setMaintenance.mockReset();
    mockUseMaintenanceContext.mockReturnValue({
      maintenance: { active: false, details: null },
      setMaintenance,
    });
  });

  it("sets active maintenance details when the API reports maintenance is active", async () => {
    mockApiFetch.mockResolvedValue({
      maintenance_active: true,
      name: "Scheduled upgrade",
      description: "DB migration",
      start_time: "2026-01-01T00:00:00Z",
      end_time: "2026-01-01T01:00:00Z",
    });

    const { result } = renderHook(() => useMaintenanceStatus());

    let status;
    await act(async () => {
      status = await result.current.refetch();
    });

    const expected = {
      active: true,
      details: {
        name: "Scheduled upgrade",
        description: "DB migration",
        startTime: "2026-01-01T00:00:00Z",
        endTime: "2026-01-01T01:00:00Z",
      },
    };
    expect(status).toEqual(expected);
    expect(setMaintenance).toHaveBeenCalledWith(expected);
  });

  it("clears maintenance details when the API reports maintenance is inactive", async () => {
    mockApiFetch.mockResolvedValue({ maintenance_active: false });

    const { result } = renderHook(() => useMaintenanceStatus());

    let status;
    await act(async () => {
      status = await result.current.refetch();
    });

    expect(status).toEqual({ active: false, details: null });
    expect(setMaintenance).toHaveBeenCalledWith({ active: false, details: null });
  });

  it("falls back to inactive when the request fails", async () => {
    mockApiFetch.mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => useMaintenanceStatus());

    let status;
    await act(async () => {
      status = await result.current.refetch();
    });

    expect(status).toEqual({ active: false, details: null });
    expect(setMaintenance).toHaveBeenCalledWith({ active: false, details: null });
  });

  it("spreads the current maintenance state from context", () => {
    mockUseMaintenanceContext.mockReturnValue({
      maintenance: { active: true, details: { name: "X" } },
      setMaintenance,
    });

    const { result } = renderHook(() => useMaintenanceStatus());

    expect(result.current.active).toBe(true);
    expect(result.current.details).toEqual({ name: "X" });
  });
});
