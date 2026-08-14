import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  formatDueAt,
  toDateInputValue,
  toTimeInputValue,
  fromDateAndTimeInputValues,
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

  it("labels the current day as today", () => {
    expect(formatDueAt(atLocalMidnight(0))).toBe("today");
  });

  it("labels the next day as tomorrow", () => {
    expect(formatDueAt(atLocalMidnight(1))).toBe("tomorrow");
  });

  it("labels the previous day as yesterday", () => {
    expect(formatDueAt(atLocalMidnight(-1))).toBe("yesterday");
  });

  it("labels a few days out as 'in N days'", () => {
    expect(formatDueAt(atLocalMidnight(3))).toBe("in 3 days");
  });

  it("labels a few days back as 'N days ago'", () => {
    expect(formatDueAt(atLocalMidnight(-3))).toBe("3 days ago");
  });

  it("labels a further-back date in whole weeks", () => {
    expect(formatDueAt(atLocalMidnight(-14))).toBe("2 weeks ago");
  });

  it("labels a further-out date in weeks, with a leftover-days remainder", () => {
    expect(formatDueAt(atLocalMidnight(9))).toBe("in 1 week, 2 days");
  });

  it("labels a further-out whole-week date without a days remainder", () => {
    expect(formatDueAt(atLocalMidnight(14))).toBe("in 2 weeks");
  });

  it("labels a further-back date in weeks, with a leftover-days remainder", () => {
    expect(formatDueAt(atLocalMidnight(-20))).toBe("2 weeks, 6 days ago");
  });

  it("labels a date beyond the week cutoff in months (future)", () => {
    expect(formatDueAt(atLocalMidnight(60))).toBe("in 2 months");
  });

  it("labels a date beyond the week cutoff in months (past)", () => {
    expect(formatDueAt(atLocalMidnight(-60))).toBe("2 months ago");
  });

  it("keeps counting months uncapped on the past side", () => {
    expect(formatDueAt(atLocalMidnight(-200))).toBe("7 months ago");
  });

  it("falls back to an absolute date beyond the month cap (future)", () => {
    // 200 days out from Wed 15 Jul 2026 is Sun 31 Jan 2027.
    expect(formatDueAt(atLocalMidnight(200))).toBe("Sun 31st Jan");
  });
});

describe("toDateInputValue", () => {
  it("returns an empty string when null", () => {
    expect(toDateInputValue(null)).toBe("");
  });

  it("formats a valid ISO string as YYYY-MM-DD", () => {
    const value = toDateInputValue("2026-05-01T08:30:00.000Z");
    expect(value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe("toTimeInputValue", () => {
  it("returns an empty string when null", () => {
    expect(toTimeInputValue(null)).toBe("");
  });

  it("formats a valid ISO string as HH:mm", () => {
    const value = toTimeInputValue("2026-05-01T08:30:00.000Z");
    expect(value).toMatch(/^\d{2}:\d{2}$/);
  });

  it("returns an empty string for the 23:59 no-time-set sentinel", () => {
    const localMidnight = new Date(2026, 4, 1, 23, 59);
    expect(toTimeInputValue(localMidnight.toISOString())).toBe("");
  });
});

describe("fromDateAndTimeInputValues", () => {
  it("returns null when both inputs are empty", () => {
    expect(fromDateAndTimeInputValues("", "")).toBeNull();
  });

  it("converts a date and time to an ISO string", () => {
    const iso = fromDateAndTimeInputValues("2026-05-01", "08:30");
    expect(iso).not.toBeNull();
    expect(new Date(iso as string).getFullYear()).toBe(2026);
  });

  it("defaults the date to today when only a time is given", () => {
    const iso = fromDateAndTimeInputValues("", "08:30") as string;
    const result = new Date(iso);
    const today = new Date();
    expect(result.getFullYear()).toBe(today.getFullYear());
    expect(result.getMonth()).toBe(today.getMonth());
    expect(result.getDate()).toBe(today.getDate());
    expect(result.getHours()).toBe(8);
    expect(result.getMinutes()).toBe(30);
  });

  it("defaults the time to 23:59 when only a date is given", () => {
    const iso = fromDateAndTimeInputValues("2026-05-01", "") as string;
    const result = new Date(iso);
    expect(result.getHours()).toBe(23);
    expect(result.getMinutes()).toBe(59);
  });

  it("round-trips through toDateInputValue and toTimeInputValue", () => {
    const original = "2026-05-01T08:30:00.000Z";
    const dateValue = toDateInputValue(original);
    const timeValue = toTimeInputValue(original);
    const roundTripped = fromDateAndTimeInputValues(dateValue, timeValue);
    expect(toDateInputValue(roundTripped)).toBe(dateValue);
    expect(toTimeInputValue(roundTripped)).toBe(timeValue);
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
