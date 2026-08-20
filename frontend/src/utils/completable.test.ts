import { describe, expect, it } from "vitest";

import { isCompletable } from "./completable";

describe("isCompletable", () => {
  it("is true when completed_at is set", () => {
    expect(isCompletable({ completed_at: "2026-01-01T00:00:00.000Z" })).toBe(true);
  });

  it("is true when is_complete is true and completed_at is absent", () => {
    expect(isCompletable({ is_complete: true })).toBe(true);
  });

  it("prefers completed_at over is_complete when both are present", () => {
    expect(isCompletable({ completed_at: null, is_complete: true })).toBe(true);
  });

  it("is false when neither field indicates completion", () => {
    expect(isCompletable({ completed_at: null, is_complete: false })).toBe(false);
  });

  it("is false for an empty object", () => {
    expect(isCompletable({})).toBe(false);
  });
});
