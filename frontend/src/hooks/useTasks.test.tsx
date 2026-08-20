import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCreateTask, useDeleteTask, useTasks, useUpdateTask } from "./useTasks";
import type { Task } from "../types";

const mockFetchTasks = vi.fn();
const mockCreateTask = vi.fn();
const mockUpdateTask = vi.fn();
const mockDeleteTask = vi.fn();

vi.mock("../api/tasks", () => ({
  fetchTasks: (...args: unknown[]) => mockFetchTasks(...args),
  createTask: (...args: unknown[]) => mockCreateTask(...args),
  updateTask: (...args: unknown[]) => mockUpdateTask(...args),
  deleteTask: (...args: unknown[]) => mockDeleteTask(...args),
}));

const task = (id: number): Task => ({ id, name: `Task ${id}` } as Task);

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useTasks", () => {
  beforeEach(() => {
    mockFetchTasks.mockReset();
    mockCreateTask.mockReset();
    mockUpdateTask.mockReset();
    mockDeleteTask.mockReset();
  });

  it("fetches tasks by default", async () => {
    mockFetchTasks.mockResolvedValue([task(1)]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useTasks(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([task(1)]);
  });

  it("does not fetch when disabled via options", () => {
    const { wrapper } = makeWrapper();
    renderHook(() => useTasks({ enabled: false }), { wrapper });
    expect(mockFetchTasks).not.toHaveBeenCalled();
  });

  it("invalidates the tasks query after creating a task", async () => {
    mockCreateTask.mockResolvedValue(task(2));
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateTask(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ name: "New task" });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["tasks"] });
  });

  it("passes the id and data through to updateTask and invalidates on success", async () => {
    mockUpdateTask.mockResolvedValue({ task: task(1) });
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdateTask(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ id: 1, data: { name: "Renamed" } });
    });

    expect(mockUpdateTask).toHaveBeenCalledWith(1, { name: "Renamed" });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["tasks"] });
  });

  it("optimistically removes a deleted task and confirms it stays gone", async () => {
    mockDeleteTask.mockResolvedValue(undefined);
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["tasks"], [task(1), task(2)]);

    const { result } = renderHook(() => useDeleteTask(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync(1);
    });

    expect(queryClient.getQueryData(["tasks"])).toEqual([task(2)]);
  });

  it("rolls back the optimistic delete when the mutation fails", async () => {
    mockDeleteTask.mockRejectedValue(new Error("boom"));
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["tasks"], [task(1), task(2)]);

    const { result } = renderHook(() => useDeleteTask(), { wrapper });

    await act(async () => {
      try {
        await result.current.mutateAsync(1);
      } catch {
        // expected
      }
    });

    expect(queryClient.getQueryData(["tasks"])).toEqual([task(1), task(2)]);
  });
});
