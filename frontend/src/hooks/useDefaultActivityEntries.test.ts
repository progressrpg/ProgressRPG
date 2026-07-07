import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useDefaultActivityEntries } from "./useDefaultActivityEntries";

const mockUseGame = vi.fn();
const mockUseTasks = vi.fn();
const mockUseFeatureFlag = vi.fn();

vi.mock("./useGame", () => ({
  useGame: () => mockUseGame(),
}));

vi.mock("./useTasks", () => ({
  useTasks: (...args: unknown[]) => mockUseTasks(...args),
}));

vi.mock("./useFeatureFlag", () => ({
  useFeatureFlag: () => mockUseFeatureFlag(),
}));

describe("useDefaultActivityEntries", () => {
  beforeEach(() => {
    mockUseGame.mockReset();
    mockUseTasks.mockReset();
    mockUseFeatureFlag.mockReset();
    mockUseFeatureFlag.mockReturnValue(true);
  });

  it("collapses activities linked to an incomplete task into a single task row", () => {
    mockUseGame.mockReturnValue({
      playerActivities: [
        { id: 1, name: "Write report", task: 10, completed_at: "2026-01-01T00:00:00Z" },
        { id: 2, name: "Write report", task: 10, completed_at: "2026-01-03T00:00:00Z" },
      ],
      characterActivities: [],
    });
    mockUseTasks.mockReturnValue({
      data: [{ id: 10, name: "Write report", is_complete: false, completed_at: null, last_worked_on: null, created_at: "2025-12-01T00:00:00Z" }],
    });

    const { result } = renderHook(() => useDefaultActivityEntries());

    expect(result.current).toHaveLength(1);
    expect(result.current[0]).toMatchObject({ name: "Write report", source: "task", taskId: 10 });
  });

  it("shows unlinked activities as themselves and drops activities linked to a completed task", () => {
    mockUseGame.mockReturnValue({
      playerActivities: [
        { id: 1, name: "Washing dishes", task: null, completed_at: "2026-01-01T00:00:00Z" },
        { id: 2, name: "Old finished task work", task: 99, completed_at: "2026-01-02T00:00:00Z" },
      ],
      characterActivities: [],
    });
    mockUseTasks.mockReturnValue({
      data: [{ id: 99, name: "Old finished task", is_complete: true, completed_at: "2026-01-02T00:00:00Z", last_worked_on: null, created_at: "2025-12-01T00:00:00Z" }],
    });

    const { result } = renderHook(() => useDefaultActivityEntries());

    expect(result.current.map((entry) => entry.name)).toEqual(["Washing dishes"]);
    expect(result.current.every((entry) => entry.source === "activity")).toBe(true);
  });

  it("includes incomplete tasks that have no activity history yet", () => {
    mockUseGame.mockReturnValue({ playerActivities: [], characterActivities: [] });
    mockUseTasks.mockReturnValue({
      data: [{ id: 5, name: "Brand new task", is_complete: false, completed_at: null, last_worked_on: null, created_at: "2026-01-05T00:00:00Z" }],
    });

    const { result } = renderHook(() => useDefaultActivityEntries());

    expect(result.current).toEqual([
      expect.objectContaining({ name: "Brand new task", source: "task", taskId: 5 }),
    ]);
  });

  it("sorts entries by recency, most recent first", () => {
    mockUseGame.mockReturnValue({
      playerActivities: [
        { id: 1, name: "Older activity", task: null, completed_at: "2026-01-01T00:00:00Z" },
        { id: 2, name: "Newer activity", task: null, completed_at: "2026-01-10T00:00:00Z" },
      ],
      characterActivities: [],
    });
    mockUseTasks.mockReturnValue({ data: [] });

    const { result } = renderHook(() => useDefaultActivityEntries());

    expect(result.current.map((entry) => entry.name)).toEqual(["Newer activity", "Older activity"]);
  });

  it("caps the default view to the 3 most recent entries", () => {
    mockUseGame.mockReturnValue({
      playerActivities: [
        { id: 1, name: "Activity 1", task: null, completed_at: "2026-01-01T00:00:00Z" },
        { id: 2, name: "Activity 2", task: null, completed_at: "2026-01-02T00:00:00Z" },
        { id: 3, name: "Activity 3", task: null, completed_at: "2026-01-03T00:00:00Z" },
        { id: 4, name: "Activity 4", task: null, completed_at: "2026-01-04T00:00:00Z" },
        { id: 5, name: "Activity 5", task: null, completed_at: "2026-01-05T00:00:00Z" },
      ],
      characterActivities: [],
    });
    mockUseTasks.mockReturnValue({ data: [] });

    const { result } = renderHook(() => useDefaultActivityEntries());

    expect(result.current.map((entry) => entry.name)).toEqual([
      "Activity 5",
      "Activity 4",
      "Activity 3",
    ]);
  });
});
