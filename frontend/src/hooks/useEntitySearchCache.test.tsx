import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEntitySearchCache } from "./useEntitySearchCache";

const mockFetchActivities = vi.fn();
const mockFetchTasks = vi.fn();
const mockUseFeatureFlag = vi.fn();

vi.mock("../api/activities", () => ({
  fetchActivities: () => mockFetchActivities(),
}));

vi.mock("../api/tasks", () => ({
  fetchTasks: () => mockFetchTasks(),
}));

vi.mock("./useFeatureFlag", () => ({
  useFeatureFlag: () => mockUseFeatureFlag(),
}));

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useEntitySearchCache", () => {
  beforeEach(() => {
    mockFetchActivities.mockReset();
    mockFetchTasks.mockReset();
    mockUseFeatureFlag.mockReset();
    mockUseFeatureFlag.mockReturnValue(false);
  });

  it("throws for an unsupported entity type", () => {
    const { wrapper } = makeWrapper();
    expect(() =>
      renderHook(() => useEntitySearchCache("bogus" as never), { wrapper })
    ).toThrow("Unsupported entity search type: bogus");
  });

  it("normalizes, dedupes, and sorts activities by frequency then recency", async () => {
    mockFetchActivities.mockResolvedValue([
      { id: 1, name: "  write report  ", completed_at: "2026-01-01T00:00:00Z" },
      { id: 2, name: "Write Report", completed_at: "2026-01-05T00:00:00Z" },
      { id: 3, name: "Read book", completed_at: "2026-01-03T00:00:00Z" },
      { id: 4, name: "" },
    ]);
    mockFetchTasks.mockResolvedValue([]);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useEntitySearchCache("activity"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.entities).toHaveLength(2);
    expect(result.current.entities[0].name).toBe("Write Report");
    expect(result.current.entities[1].name).toBe("Read book");
  });

  it("includes completed tasks when fetching for the task type directly", async () => {
    mockFetchTasks.mockResolvedValue([
      { id: 1, name: "Open task", is_complete: false, completed_at: null },
      { id: 2, name: "Done task", is_complete: true, completed_at: "2026-01-01T00:00:00Z" },
    ]);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useEntitySearchCache("task"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const names = result.current.entities.map((e) => e.name).sort();
    expect(names).toEqual(["Done task", "Open task"]);
  });

  it("merges task suggestions into activity entities when the tasks feature flag is enabled", async () => {
    mockUseFeatureFlag.mockReturnValue(true);
    mockFetchActivities.mockResolvedValue([{ id: 1, name: "Write report", completed_at: "2026-01-01T00:00:00Z" }]);
    mockFetchTasks.mockResolvedValue([{ id: 5, name: "Plan trip", is_complete: false, completed_at: null }]);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useEntitySearchCache("activity"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    await waitFor(() =>
      expect(result.current.entities.some((e) => e.name === "Plan trip")).toBe(true)
    );

    const names = result.current.entities.map((e) => e.name);
    expect(names).toContain("Write report");
    expect(names).toContain("Plan trip");
  });

  it("does not fetch task suggestions when the tasks feature flag is disabled", async () => {
    mockUseFeatureFlag.mockReturnValue(false);
    mockFetchActivities.mockResolvedValue([]);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useEntitySearchCache("activity"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFetchTasks).not.toHaveBeenCalled();
  });

  it("adds an optimistic entity to the activity cache, incrementing frequency on repeat inserts", async () => {
    mockFetchActivities.mockResolvedValue([]);

    const { queryClient, wrapper } = makeWrapper();
    const { result } = renderHook(() => useEntitySearchCache("activity"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    act(() => {
      result.current.addEntityToCache("New activity");
    });
    let cached = queryClient.getQueryData<{ name: string; isOptimistic: boolean; frequency: number }[]>([
      "entity-search",
      "activity",
      "activities",
    ]);
    expect(cached).toHaveLength(1);
    expect(cached?.[0]).toMatchObject({ name: "New activity", isOptimistic: true, frequency: 0 });

    act(() => {
      result.current.addEntityToCache("New activity");
    });
    cached = queryClient.getQueryData(["entity-search", "activity", "activities"]);
    expect(cached).toHaveLength(1);
    expect(cached?.[0].frequency).toBe(1);
  });

  it("returns null from addEntityToCache for the task entity type", async () => {
    mockFetchTasks.mockResolvedValue([]);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useEntitySearchCache("task"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    let added;
    act(() => {
      added = result.current.addEntityToCache("Ignored");
    });
    expect(added).toBeNull();
  });

  it("returns null from addEntityToCache when the normalized name is empty", async () => {
    mockFetchActivities.mockResolvedValue([]);

    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useEntitySearchCache("activity"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    let added;
    act(() => {
      added = result.current.addEntityToCache("   ");
    });
    expect(added).toBeNull();
  });
});
