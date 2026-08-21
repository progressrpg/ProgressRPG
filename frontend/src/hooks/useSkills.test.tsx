import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCreateSkill, useDeleteSkill, useSkills, useUpdateSkill } from "./useSkills";
import type { PlayerSkill } from "../types";

const mockFetchSkills = vi.fn();
const mockCreateSkill = vi.fn();
const mockUpdateSkill = vi.fn();
const mockDeleteSkill = vi.fn();

vi.mock("../api/skills", () => ({
  fetchSkills: (...args: unknown[]) => mockFetchSkills(...args),
  createSkill: (...args: unknown[]) => mockCreateSkill(...args),
  updateSkill: (...args: unknown[]) => mockUpdateSkill(...args),
  deleteSkill: (...args: unknown[]) => mockDeleteSkill(...args),
}));

const skill = (id: number): PlayerSkill => ({ id, name: `Skill ${id}` } as PlayerSkill);

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useSkills", () => {
  beforeEach(() => {
    mockFetchSkills.mockReset();
    mockCreateSkill.mockReset();
    mockUpdateSkill.mockReset();
    mockDeleteSkill.mockReset();
  });

  it("fetches skills", async () => {
    mockFetchSkills.mockResolvedValue([skill(1)]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useSkills(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([skill(1)]);
  });

  it("invalidates skills after creating one", async () => {
    mockCreateSkill.mockResolvedValue(skill(2));
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateSkill(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ name: "New" });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["skills"] });
  });

  it("passes id and data through to updateSkill", async () => {
    mockUpdateSkill.mockResolvedValue(skill(1));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useUpdateSkill(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ id: 1, data: { name: "Renamed" } });
    });

    expect(mockUpdateSkill).toHaveBeenCalledWith(1, { name: "Renamed" });
  });

  it("optimistically removes a deleted skill and rolls back on failure", async () => {
    mockDeleteSkill.mockRejectedValue(new Error("boom"));
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["skills"], [skill(1), skill(2)]);

    const { result } = renderHook(() => useDeleteSkill(), { wrapper });
    await act(async () => {
      try {
        await result.current.mutateAsync(1);
      } catch {
        // expected
      }
    });

    expect(queryClient.getQueryData(["skills"])).toEqual([skill(1), skill(2)]);
  });

  it("keeps an optimistically deleted skill removed on success", async () => {
    mockDeleteSkill.mockResolvedValue(undefined);
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["skills"], [skill(1), skill(2)]);

    const { result } = renderHook(() => useDeleteSkill(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync(1);
    });

    expect(queryClient.getQueryData(["skills"])).toEqual([skill(2)]);
  });
});
