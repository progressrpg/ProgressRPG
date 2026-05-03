import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEntitySearchCache } from "./useEntitySearchCache";

const fetchActivities = vi.fn();

vi.mock("../api/activities", () => ({
  fetchActivities: () => fetchActivities(),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("useEntitySearchCache", () => {
  beforeEach(() => {
    fetchActivities.mockReset();
  });

  it("loads once and deduplicates activities by name", async () => {
    fetchActivities.mockResolvedValue([
      { id: 1, name: "Write docs", completed_at: "2026-05-03T09:00:00Z" },
      { id: 2, name: "write docs", completed_at: "2026-05-02T09:00:00Z" },
      { id: 3, name: "Wash dishes", completed_at: "2026-05-03T08:00:00Z" },
      { id: 4, name: " ", completed_at: "2026-05-03T07:00:00Z" },
    ]);

    const { result } = renderHook(() => useEntitySearchCache("activity"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.entities).toEqual([
        {
          id: 1,
          name: "Write docs",
          completedAt: "2026-05-03T09:00:00Z",
          isOptimistic: false,
        },
        {
          id: 3,
          name: "Wash dishes",
          completedAt: "2026-05-03T08:00:00Z",
          isOptimistic: false,
        },
      ]);
    });

    expect(fetchActivities).toHaveBeenCalledTimes(1);
  });

  it("adds optimistic entities to the in-memory cache", async () => {
    fetchActivities.mockResolvedValue([
      { id: 1, name: "Write docs", completed_at: "2026-05-03T09:00:00Z" },
    ]);

    const { result } = renderHook(() => useEntitySearchCache("activity"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.entities).toHaveLength(1);
    });

    act(() => {
      result.current.addEntityToCache("Walk dog");
    });

    await waitFor(() => {
      expect(result.current.entities).toEqual([
        {
          id: 1,
          name: "Write docs",
          completedAt: "2026-05-03T09:00:00Z",
          isOptimistic: false,
        },
        {
          id: "activity-walk dog",
          name: "Walk dog",
          completedAt: null,
          isOptimistic: true,
        },
      ]);
    });
  });
});
