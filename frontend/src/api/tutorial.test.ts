import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchTutorialSteps, markTutorialStepsSeen } from "./tutorial";
import { apiFetch } from "../utils/api";
import type { TutorialStep } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchTutorialSteps", () => {
  it("fetches the tutorial steps list", async () => {
    const steps = [{ id: 1 }] as TutorialStep[];
    mockedApiFetch.mockResolvedValueOnce(steps);

    const result = await fetchTutorialSteps();

    expect(mockedApiFetch).toHaveBeenCalledWith("/tutorial-steps/");
    expect(result).toBe(steps);
  });
});

describe("markTutorialStepsSeen", () => {
  it("posts the seen step ids", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await markTutorialStepsSeen([1, 2, 3]);

    expect(mockedApiFetch).toHaveBeenCalledWith("/me/mark_tutorial_steps_seen/", {
      method: "POST",
      body: JSON.stringify({ step_ids: [1, 2, 3] }),
    });
  });
});
