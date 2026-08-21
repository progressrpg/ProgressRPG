import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createActivity,
  deleteActivity,
  fetchActivities,
  fetchActivity,
  logOfflineActivity,
  updateActivity,
} from "./activities";
import { apiFetch } from "../utils/api";
import type { PlayerActivity } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchActivities", () => {
  it("returns all results when there is a single page", async () => {
    const activities = [{ id: 1 }, { id: 2 }] as PlayerActivity[];
    mockedApiFetch.mockResolvedValueOnce({ results: activities, next: null });

    const result = await fetchActivities();

    expect(result).toEqual(activities);
    expect(mockedApiFetch).toHaveBeenCalledTimes(1);
    expect(mockedApiFetch).toHaveBeenCalledWith("/player-activities/?page=1");
  });

  it("follows pagination across multiple pages", async () => {
    const first = [{ id: 1 }] as PlayerActivity[];
    const second = [{ id: 2 }] as PlayerActivity[];
    mockedApiFetch
      .mockResolvedValueOnce({ results: first, next: "https://api.example.com/?page=2" })
      .mockResolvedValueOnce({ results: second, next: null });

    const result = await fetchActivities();

    expect(result).toEqual([...first, ...second]);
    expect(mockedApiFetch).toHaveBeenNthCalledWith(1, "/player-activities/?page=1");
    expect(mockedApiFetch).toHaveBeenNthCalledWith(2, "/player-activities/?page=2");
  });

  it("treats a missing results array as empty rather than throwing", async () => {
    mockedApiFetch.mockResolvedValueOnce({ next: null });

    const result = await fetchActivities();

    expect(result).toEqual([]);
  });

  it("stops once next is falsy even if results is empty", async () => {
    mockedApiFetch.mockResolvedValueOnce({ results: [], next: null });

    const result = await fetchActivities();

    expect(result).toEqual([]);
    expect(mockedApiFetch).toHaveBeenCalledTimes(1);
  });
});

describe("fetchActivity", () => {
  it("fetches a single activity by id", async () => {
    const activity = { id: 9 } as PlayerActivity;
    mockedApiFetch.mockResolvedValueOnce(activity);

    const result = await fetchActivity(9);

    expect(mockedApiFetch).toHaveBeenCalledWith("/player-activities/9/");
    expect(result).toBe(activity);
  });
});

describe("createActivity", () => {
  it("posts activity data", async () => {
    const created = { id: 1 } as PlayerActivity;
    mockedApiFetch.mockResolvedValueOnce(created);

    const result = await createActivity({ description: "test" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/player-activities/", {
      method: "POST",
      body: JSON.stringify({ description: "test" }),
    });
    expect(result).toBe(created);
  });
});

describe("updateActivity", () => {
  it("patches activity data by id", async () => {
    const updated = { id: 2 } as PlayerActivity;
    mockedApiFetch.mockResolvedValueOnce(updated);

    const result = await updateActivity(2, { description: "updated" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/player-activities/2/", {
      method: "PATCH",
      body: JSON.stringify({ description: "updated" }),
    });
    expect(result).toBe(updated);
  });
});

describe("deleteActivity", () => {
  it("deletes an activity by id", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await deleteActivity(4);

    expect(mockedApiFetch).toHaveBeenCalledWith("/player-activities/4/", {
      method: "DELETE",
    });
  });
});

describe("logOfflineActivity", () => {
  it("posts the offline activity payload to the log_offline endpoint", async () => {
    const response = { activity: { id: 1 } };
    mockedApiFetch.mockResolvedValueOnce(response);
    const payload = {
      name: "Reading",
      started_at: "2026-08-20T10:00:00Z",
      completed_at: "2026-08-20T10:30:00Z",
    };

    const result = await logOfflineActivity(payload);

    expect(mockedApiFetch).toHaveBeenCalledWith("/player-activities/log_offline/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    expect(result).toBe(response);
  });
});
