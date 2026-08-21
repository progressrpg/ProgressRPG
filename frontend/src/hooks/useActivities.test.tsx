import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useActivities,
  useChangeActivitySkill,
  useChangeActivityTask,
  useCreateActivity,
  useDeleteActivity,
  useLogOfflineActivity,
  useUpdateActivity,
} from "./useActivities";
import type { PlayerActivity } from "../types";

const mockFetchActivities = vi.fn();
const mockCreateActivity = vi.fn();
const mockUpdateActivity = vi.fn();
const mockDeleteActivity = vi.fn();
const mockLogOfflineActivity = vi.fn();

vi.mock("../api/activities", () => ({
  fetchActivities: (...args: unknown[]) => mockFetchActivities(...args),
  createActivity: (...args: unknown[]) => mockCreateActivity(...args),
  updateActivity: (...args: unknown[]) => mockUpdateActivity(...args),
  deleteActivity: (...args: unknown[]) => mockDeleteActivity(...args),
  logOfflineActivity: (...args: unknown[]) => mockLogOfflineActivity(...args),
}));

const activity = (id: number): PlayerActivity => ({ id, name: `Activity ${id}` } as PlayerActivity);

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useActivities", () => {
  beforeEach(() => {
    mockFetchActivities.mockReset();
    mockCreateActivity.mockReset();
    mockUpdateActivity.mockReset();
    mockDeleteActivity.mockReset();
    mockLogOfflineActivity.mockReset();
  });

  it("fetches activities", async () => {
    mockFetchActivities.mockResolvedValue([activity(1)]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useActivities(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([activity(1)]);
  });

  it("invalidates activities after creating one", async () => {
    mockCreateActivity.mockResolvedValue(activity(2));
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateActivity(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ name: "New" });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["activities"] });
  });

  it("invalidates both activities and tasks after logging an offline activity", async () => {
    mockLogOfflineActivity.mockResolvedValue(activity(3));
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useLogOfflineActivity(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ started_at: "2026-01-01T00:00:00Z", completed_at: "2026-01-01T00:10:00Z" });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["activities"] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["tasks"] });
  });

  it("passes activityId and data through to updateActivity", async () => {
    mockUpdateActivity.mockResolvedValue(activity(1));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useUpdateActivity(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ activityId: 1, data: { name: "Renamed" } });
    });

    expect(mockUpdateActivity).toHaveBeenCalledWith(1, { name: "Renamed" });
  });

  it("changes an activity's skill via updateActivity", async () => {
    mockUpdateActivity.mockResolvedValue(activity(1));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useChangeActivitySkill(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ activityId: 1, skillId: 9 });
    });

    expect(mockUpdateActivity).toHaveBeenCalledWith(1, { skill_id: 9 });
  });

  it("changes an activity's task via updateActivity, including clearing it to null", async () => {
    mockUpdateActivity.mockResolvedValue(activity(1));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useChangeActivityTask(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ activityId: 1, taskId: null });
    });

    expect(mockUpdateActivity).toHaveBeenCalledWith(1, { task_id: null });
  });

  it("optimistically removes a deleted activity and rolls back on failure", async () => {
    mockDeleteActivity.mockRejectedValue(new Error("boom"));
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["activities"], [activity(1), activity(2)]);

    const { result } = renderHook(() => useDeleteActivity(), { wrapper });
    await act(async () => {
      try {
        await result.current.mutateAsync(1);
      } catch {
        // expected
      }
    });

    expect(queryClient.getQueryData(["activities"])).toEqual([activity(1), activity(2)]);
  });

  it("keeps an optimistically deleted activity removed on success", async () => {
    mockDeleteActivity.mockResolvedValue(undefined);
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["activities"], [activity(1), activity(2)]);

    const { result } = renderHook(() => useDeleteActivity(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync(1);
    });

    expect(queryClient.getQueryData(["activities"])).toEqual([activity(2)]);
  });
});
