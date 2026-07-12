import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  formatDueAt,
  toDatetimeLocalValue,
  fromDatetimeLocalValue,
  isOverdue,
} from "./formatUtils";

describe("formatDueAt", () => {
  // Anchor "today" to a fixed, mid-week local date so day-diff buckets are deterministic.
  const today = new Date(2026, 6, 15, 12, 0, 0); // Wed 15 Jul 2026, local time

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(today);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const atLocalMidnight = (daysFromToday: number) => {
    const d = new Date(today);
    d.setDate(d.getDate() + daysFromToday);
    d.setHours(9, 0, 0, 0);
    return d.toISOString();
  };

  it("returns '-' when null", () => {
    expect(formatDueAt(null)).toBe("-");
  });

  it("labels the current day as Today", () => {
    expect(formatDueAt(atLocalMidnight(0))).toBe("Today");
  });

  it("labels the next day as Tomorrow", () => {
    expect(formatDueAt(atLocalMidnight(1))).toBe("Tomorrow");
  });

  it("labels the previous day as Yesterday", () => {
    expect(formatDueAt(atLocalMidnight(-1))).toBe("Yesterday");
  });

  it("labels a few days out as 'in N days'", () => {
    expect(formatDueAt(atLocalMidnight(3))).toBe("in 3 days");
  });

  it("labels a few days back as 'N days ago'", () => {
    expect(formatDueAt(atLocalMidnight(-3))).toBe("3 days ago");
  });

  it("labels a further-back date in weeks", () => {
    expect(formatDueAt(atLocalMidnight(-14))).toBe("2 weeks ago");
  });

  it("labels a further-out date as an absolute weekday/day/month", () => {
    // 9 days out from Wed 15 Jul 2026 is Fri 24 Jul 2026.
    expect(formatDueAt(atLocalMidnight(9))).toBe("Fri 24th Jul");
  });
});

describe("toDatetimeLocalValue", () => {
  it("returns an empty string when null", () => {
    expect(toDatetimeLocalValue(null)).toBe("");
  });

  it("formats a valid ISO string as YYYY-MM-DDTHH:mm", () => {
    const value = toDatetimeLocalValue("2026-05-01T08:30:00.000Z");
    expect(value).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });
});

describe("fromDatetimeLocalValue", () => {
  it("returns null for an empty string", () => {
    expect(fromDatetimeLocalValue("")).toBeNull();
  });

  it("converts a datetime-local value to an ISO string", () => {
    const iso = fromDatetimeLocalValue("2026-05-01T08:30");
    expect(iso).not.toBeNull();
    expect(new Date(iso as string).getFullYear()).toBe(2026);
  });

  it("round-trips through toDatetimeLocalValue", () => {
    const original = "2026-05-01T08:30:00.000Z";
    const localValue = toDatetimeLocalValue(original);
    const roundTripped = fromDatetimeLocalValue(localValue);
    expect(toDatetimeLocalValue(roundTripped)).toBe(localValue);
  });
});

describe("isOverdue", () => {
  it("is false when due_at is null", () => {
    expect(isOverdue(null, false)).toBe(false);
  });

  it("is false when the task is complete, even if due_at is in the past", () => {
    expect(isOverdue("2020-01-01T00:00:00.000Z", true)).toBe(false);
  });

  it("is true when due_at is in the past and the task is incomplete", () => {
    expect(isOverdue("2020-01-01T00:00:00.000Z", false)).toBe(true);
  });

  it("is false when due_at is in the future", () => {
    const future = new Date(Date.now() + 1000 * 60 * 60 * 24).toISOString();
    expect(isOverdue(future, false)).toBe(false);
  });
});
