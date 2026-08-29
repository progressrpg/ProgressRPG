import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchMaintenanceStatus } from "./maintenance";
import { apiFetch } from "../utils/api";
import type { MaintenanceStatusApiResponse } from "./maintenance";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchMaintenanceStatus", () => {
  it("fetches the maintenance status", async () => {
    const response: MaintenanceStatusApiResponse = { maintenance_active: false };
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await fetchMaintenanceStatus();

    expect(mockedApiFetch).toHaveBeenCalledWith("/maintenance_status/");
    expect(result).toBe(response);
  });
});
