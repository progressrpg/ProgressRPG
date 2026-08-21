import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  formatDueAt,
  formatDuration,
  formatDurationShort,
  formatPublishedAt,
  formatRewardDuration,
  fromDateAndTimeInputValues,
  isOverdue,
  pluralize,
  toDateInputValue,
  toTimeInputValue,
} from "./formatUtils";

describe("formatDuration", () => {
  it("formats seconds under a minute as mm:ss", () => {
    expect(formatDuration(5)).toBe("0:05");
  });

  it("formats minutes and seconds without a leading zero on minutes", () => {
    expect(formatDuration(125)).toBe("2:05");
  });

  it("formats hours as h:mm:ss with padded minutes", () => {
    expect(formatDuration(3665)).toBe("1:01:05");
  });
});

describe("formatDurationShort", () => {
  it("formats sub-minute durations as seconds", () => {
    expect(formatDurationShort(45)).toBe("45s");
  });

  it("formats whole minutes without a seconds remainder", () => {
    expect(formatDurationShort(120)).toBe("2m");
  });

  it("formats minutes with a seconds remainder", () => {
    expect(formatDurationShort(125)).toBe("2m 5s");
  });

  it("formats whole hours without a minutes remainder", () => {
    expect(formatDurationShort(7200)).toBe("2h");
  });

  it("formats hours with a minutes remainder", () => {
    expect(formatDurationShort(7260)).toBe("2h 1m");
  });
});

describe("pluralize", () => {
  it("uses the singular form for a count of 1", () => {
    expect(pluralize(1, "day")).toBe("day");
  });

  it("uses the default plural form (singular + s) for other counts", () => {
    expect(pluralize(0, "day")).toBe("days");
    expect(pluralize(3, "day")).toBe("days");
  });

  it("uses an explicit irregular plural when given", () => {
    expect(pluralize(3, "child", "children")).toBe("children");
  });
});

describe("formatRewardDuration", () => {
  it("clamps negative durations to zero seconds", () => {
    expect(formatRewardDuration(-5)).toBe("0 seconds");
  });

  it("formats a sub-minute duration in seconds, pluralizing correctly", () => {
    expect(formatRewardDuration(1)).toBe("1 second");
    expect(formatRewardDuration(45)).toBe("45 seconds");
  });

  it("formats minutes with a seconds remainder", () => {
    expect(formatRewardDuration(90)).toBe("1 minute 30 seconds");
  });

  it("formats whole minutes without a seconds remainder", () => {
    expect(formatRewardDuration(120)).toBe("2 minutes");
  });

  it("formats hours with a minutes remainder, dropping any seconds", () => {
    expect(formatRewardDuration(3665)).toBe("1 hour 1 minute");
  });

  it("formats whole hours without a minutes remainder", () => {
    expect(formatRewardDuration(7200)).toBe("2 hours");
  });
});

describe("formatPublishedAt", () => {
  it("returns null when publishedAt is null", () => {
    expect(formatPublishedAt(null)).toBeNull();
  });

  it("returns null for an invalid date string", () => {
    expect(formatPublishedAt("not-a-date")).toBeNull();
  });

  it("formats a valid ISO string as a date and time", () => {
    const result = formatPublishedAt("2026-05-01T08:30:00.000Z");
    expect(result).toMatch(/\d{1,2}.*2026.*\d{1,2}:\d{2}/);
  });
});

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

  it("uses the 'th' ordinal suffix for the 11th-13th of the month", () => {
    // Well beyond the 180-day month cutoff from Wed 15 Jul 2026, so this falls
    // back to an absolute date.
    const mar12 = new Date(2027, 2, 12, 9, 0, 0);
    expect(formatDueAt(mar12.toISOString())).toBe("Fri 12th Mar");
  });

  it("uses the 'nd' ordinal suffix for the 2nd of the month", () => {
    const mar2 = new Date(2027, 2, 2, 9, 0, 0);
    expect(formatDueAt(mar2.toISOString())).toBe("Tue 2nd Mar");
  });

  it("uses the 'rd' ordinal suffix for the 3rd of the month", () => {
    const mar3 = new Date(2027, 2, 3, 9, 0, 0);
    expect(formatDueAt(mar3.toISOString())).toBe("Wed 3rd Mar");
  });

  it("uses the default 'th' ordinal suffix outside 1st/2nd/3rd/11th-13th", () => {
    const mar15 = new Date(2027, 2, 15, 9, 0, 0);
    expect(formatDueAt(mar15.toISOString())).toBe("Mon 15th Mar");
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
