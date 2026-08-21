import { afterEach, describe, expect, it, vi } from "vitest";

import { deleteAccount, downloadUserData, fetchDailyGoals, updatePlayer } from "./player";
import { apiFetch } from "../utils/api";
import type { Player } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

describe("updatePlayer", () => {
  it("patches player data", async () => {
    const player = { id: 1, level: 2 } as Player;
    mockedApiFetch.mockResolvedValueOnce(player);

    const result = await updatePlayer({ level: 2 });

    expect(mockedApiFetch).toHaveBeenCalledWith("/me/player/", {
      method: "PATCH",
      body: JSON.stringify({ level: 2 }),
    });
    expect(result).toBe(player);
  });
});

describe("deleteAccount", () => {
  it("issues a DELETE to the delete_account endpoint", async () => {
    mockedApiFetch.mockResolvedValueOnce({ deleted: true });

    const result = await deleteAccount();

    expect(mockedApiFetch).toHaveBeenCalledWith("/delete_account/", {
      method: "DELETE",
    });
    expect(result).toEqual({ deleted: true });
  });
});

describe("fetchDailyGoals", () => {
  it("fetches the daily goals summary", async () => {
    const goals = { goals: null };
    mockedApiFetch.mockResolvedValueOnce(goals);

    const result = await fetchDailyGoals();

    expect(mockedApiFetch).toHaveBeenCalledWith("/me/daily_goals/");
    expect(result).toBe(goals);
  });
});

describe("downloadUserData", () => {
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    vi.restoreAllMocks();
  });

  function mockRawResponse({
    contentDisposition,
  }: {
    contentDisposition: string | null;
  }) {
    const blob = new Blob(["data"], { type: "application/json" });
    mockedApiFetch.mockResolvedValueOnce({
      blob: () => Promise.resolve(blob),
      headers: {
        get: (name: string) => (name === "Content-Disposition" ? contentDisposition : null),
      },
    });
    return blob;
  }

  it("requests the raw response with the correct options", async () => {
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = vi.fn();
    mockRawResponse({ contentDisposition: 'attachment; filename="export.json"' });

    await downloadUserData();

    expect(mockedApiFetch).toHaveBeenCalledWith("/download_user_data/", {
      method: "GET",
      responseType: "raw",
    });
  });

  it("triggers a download using the filename from Content-Disposition", async () => {
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = vi.fn();
    mockRawResponse({ contentDisposition: 'attachment; filename="export.json"' });

    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const result = await downloadUserData();

    expect(result).toEqual({ success: true });
    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  it("falls back to a dated filename when Content-Disposition is missing", async () => {
    URL.createObjectURL = vi.fn(() => "blob:mock-url");
    URL.revokeObjectURL = vi.fn();
    mockRawResponse({ contentDisposition: null });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const setAttributeSpy = vi.spyOn(HTMLAnchorElement.prototype, "setAttribute");

    await downloadUserData();

    const downloadCall = setAttributeSpy.mock.calls.find(([attr]) => attr === "download");
    expect(downloadCall?.[1]).toMatch(/^user-data-\d{4}-\d{2}-\d{2}\.json$/);
  });
});
