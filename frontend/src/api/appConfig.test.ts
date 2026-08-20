import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchAppConfig } from "./appConfig";
import { apiFetch } from "../utils/api";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchAppConfig", () => {
  it("fetches the app config", async () => {
    const config = { feature_flags: {} };
    mockedApiFetch.mockResolvedValueOnce(config);

    const result = await fetchAppConfig();

    expect(mockedApiFetch).toHaveBeenCalledWith("/app_config/");
    expect(result).toBe(config);
  });
});
