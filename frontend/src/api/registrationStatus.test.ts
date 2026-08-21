import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchRegistrationStatus } from "./registrationStatus";
import { API_BASE_URL } from "../config";

const EXPECTED_URL = `${API_BASE_URL}/api/v1/registration_status/`;

describe("fetchRegistrationStatus", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches the registration status endpoint and returns the parsed body", async () => {
    const status = { open: true };
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(status),
    });
    vi.stubGlobal("fetch", mockFetch);

    const result = await fetchRegistrationStatus();

    expect(mockFetch).toHaveBeenCalledWith(EXPECTED_URL);
    expect(result).toEqual(status);
  });

  it("throws when the response is not ok", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({}),
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(fetchRegistrationStatus()).rejects.toThrow(
      "Unable to fetch registration status"
    );
  });
});
