import { beforeEach, describe, expect, it } from "vitest";

import { TASKS_HIDE_COMPLETED_KEY, clearUserPreferences } from "./userPreferences";

describe("clearUserPreferences", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("removes the hide-completed-tasks preference", () => {
    localStorage.setItem(TASKS_HIDE_COMPLETED_KEY, "true");

    clearUserPreferences();

    expect(localStorage.getItem(TASKS_HIDE_COMPLETED_KEY)).toBeNull();
  });

  it("is a no-op when no preference was stored", () => {
    expect(() => clearUserPreferences()).not.toThrow();
    expect(localStorage.getItem(TASKS_HIDE_COMPLETED_KEY)).toBeNull();
  });
});
