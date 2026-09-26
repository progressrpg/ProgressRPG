import { afterEach, describe, expect, it, vi } from "vitest";

import {
  completeTimer,
  labelActivity,
  resetTimer,
  setActivity,
  startTimer,
} from "./activityTimers";
import { apiFetch } from "../utils/api";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("setActivity", () => {
  it("posts the activity payload, filling in defaults", async () => {
    const response = { activity_timer: { activity: { id: 1 } } };
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await setActivity({ activityName: "Writing" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/activity_timers/set_activity/", {
      method: "POST",
      body: JSON.stringify({
        activityName: "Writing",
        task_id: null,
        duration: 0,
        limitSeconds: null,
        limitReason: null,
        start: false,
      }),
    });
    expect(result).toBe(response);
  });

  it("passes through every optional field when given", async () => {
    mockedApiFetch.mockResolvedValueOnce({});

    await setActivity({
      activityName: "Reading",
      taskId: 7,
      duration: 0,
      limitSeconds: 1800,
      limitReason: "free_limit",
      start: true,
    });

    expect(mockedApiFetch).toHaveBeenCalledWith("/activity_timers/set_activity/", {
      method: "POST",
      body: JSON.stringify({
        activityName: "Reading",
        task_id: 7,
        duration: 0,
        limitSeconds: 1800,
        limitReason: "free_limit",
        start: true,
      }),
    });
  });
});

describe("labelActivity", () => {
  it("posts the new name and task id", async () => {
    const response = { activity_timer: { activity: { id: 1, name: "Renamed" } } };
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await labelActivity("Renamed", 3);

    expect(mockedApiFetch).toHaveBeenCalledWith("/activity_timers/label_activity/", {
      method: "POST",
      body: JSON.stringify({ activityName: "Renamed", task_id: 3 }),
    });
    expect(result).toBe(response);
  });

  it("defaults taskId to null", async () => {
    mockedApiFetch.mockResolvedValueOnce({});

    await labelActivity("Renamed");

    expect(mockedApiFetch).toHaveBeenCalledWith("/activity_timers/label_activity/", {
      method: "POST",
      body: JSON.stringify({ activityName: "Renamed", task_id: null }),
    });
  });
});

describe("startTimer", () => {
  it("posts to the start endpoint", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await startTimer();

    expect(mockedApiFetch).toHaveBeenCalledWith("/activity_timers/start/", {
      method: "POST",
    });
  });
});

describe("resetTimer", () => {
  it("posts to the reset endpoint", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await resetTimer();

    expect(mockedApiFetch).toHaveBeenCalledWith("/activity_timers/reset/", {
      method: "POST",
    });
  });
});

describe("completeTimer", () => {
  it("posts activityName, elapsedSeconds, and source", async () => {
    const response = { duration_seconds: 120, xp_gained: 10 };
    mockedApiFetch.mockResolvedValueOnce(response);

    const result = await completeTimer("Writing", 120, "manual");

    expect(mockedApiFetch).toHaveBeenCalledWith("/activity_timers/complete/", {
      method: "POST",
      body: JSON.stringify({
        activityName: "Writing",
        elapsedSeconds: 120,
        source: "manual",
      }),
    });
    expect(result).toBe(response);
  });

  it("defaults source to manual", async () => {
    mockedApiFetch.mockResolvedValueOnce({});

    await completeTimer(undefined, 30);

    expect(mockedApiFetch).toHaveBeenCalledWith("/activity_timers/complete/", {
      method: "POST",
      body: JSON.stringify({
        activityName: undefined,
        elapsedSeconds: 30,
        source: "manual",
      }),
    });
  });
});
