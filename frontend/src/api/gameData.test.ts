import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchInfo } from "./gameData";
import { apiFetch } from "../utils/api";
import type { FetchInfoResponse } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchInfo", () => {
  it("fetches the bootstrap payload", async () => {
    const response = { build_number: "1.2.3" } as FetchInfoResponse;
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await fetchInfo();

    expect(mockedApiFetch).toHaveBeenCalledWith("/fetch_info/");
    expect(result).toBe(response);
  });
});
