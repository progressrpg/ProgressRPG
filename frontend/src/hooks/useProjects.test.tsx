import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCreateProject, useDeleteProject, useProjects, useUpdateProject } from "./useProjects";
import type { Project } from "../types";

const mockFetchProjects = vi.fn();
const mockCreateProject = vi.fn();
const mockUpdateProject = vi.fn();
const mockDeleteProject = vi.fn();

vi.mock("../api/projects", () => ({
  fetchProjects: (...args: unknown[]) => mockFetchProjects(...args),
  createProject: (...args: unknown[]) => mockCreateProject(...args),
  updateProject: (...args: unknown[]) => mockUpdateProject(...args),
  deleteProject: (...args: unknown[]) => mockDeleteProject(...args),
}));

const project = (id: number): Project => ({ id, name: `Project ${id}` } as Project);

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useProjects", () => {
  beforeEach(() => {
    mockFetchProjects.mockReset();
    mockCreateProject.mockReset();
    mockUpdateProject.mockReset();
    mockDeleteProject.mockReset();
  });

  it("fetches projects", async () => {
    mockFetchProjects.mockResolvedValue([project(1)]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useProjects(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([project(1)]);
  });

  it("invalidates projects after creating one", async () => {
    mockCreateProject.mockResolvedValue(project(2));
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateProject(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ name: "New" });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["projects"] });
  });

  it("passes id and data through to updateProject", async () => {
    mockUpdateProject.mockResolvedValue(project(1));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useUpdateProject(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ id: 1, data: { name: "Renamed" } });
    });

    expect(mockUpdateProject).toHaveBeenCalledWith(1, { name: "Renamed" });
  });

  it("optimistically removes a deleted project and rolls back on failure", async () => {
    mockDeleteProject.mockRejectedValue(new Error("boom"));
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["projects"], [project(1), project(2)]);

    const { result } = renderHook(() => useDeleteProject(), { wrapper });
    await act(async () => {
      try {
        await result.current.mutateAsync(1);
      } catch {
        // expected
      }
    });

    expect(queryClient.getQueryData(["projects"])).toEqual([project(1), project(2)]);
  });

  it("keeps an optimistically deleted project removed on success", async () => {
    mockDeleteProject.mockResolvedValue(undefined);
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["projects"], [project(1), project(2)]);

    const { result } = renderHook(() => useDeleteProject(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync(1);
    });

    expect(queryClient.getQueryData(["projects"])).toEqual([project(2)]);
  });
});
