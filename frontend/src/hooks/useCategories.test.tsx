import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCategories, useCreateCategory, useDeleteCategory, useUpdateCategory } from "./useCategories";
import type { Category } from "../types";

const mockFetchCategories = vi.fn();
const mockCreateCategory = vi.fn();
const mockUpdateCategory = vi.fn();
const mockDeleteCategory = vi.fn();

vi.mock("../api/categories", () => ({
  fetchCategories: (...args: unknown[]) => mockFetchCategories(...args),
  createCategory: (...args: unknown[]) => mockCreateCategory(...args),
  updateCategory: (...args: unknown[]) => mockUpdateCategory(...args),
  deleteCategory: (...args: unknown[]) => mockDeleteCategory(...args),
}));

const category = (id: number): Category => ({ id, name: `Category ${id}` } as Category);

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useCategories", () => {
  beforeEach(() => {
    mockFetchCategories.mockReset();
    mockCreateCategory.mockReset();
    mockUpdateCategory.mockReset();
    mockDeleteCategory.mockReset();
  });

  it("fetches categories", async () => {
    mockFetchCategories.mockResolvedValue([category(1)]);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useCategories(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([category(1)]);
  });

  it("invalidates categories after creating one", async () => {
    mockCreateCategory.mockResolvedValue(category(2));
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useCreateCategory(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ name: "New" });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["categories"] });
  });

  it("passes id and data through to updateCategory", async () => {
    mockUpdateCategory.mockResolvedValue(category(1));
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useUpdateCategory(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ id: 1, data: { name: "Renamed" } });
    });

    expect(mockUpdateCategory).toHaveBeenCalledWith(1, { name: "Renamed" });
  });

  it("optimistically removes a deleted category and rolls back on failure", async () => {
    mockDeleteCategory.mockRejectedValue(new Error("boom"));
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["categories"], [category(1), category(2)]);

    const { result } = renderHook(() => useDeleteCategory(), { wrapper });
    await act(async () => {
      try {
        await result.current.mutateAsync(1);
      } catch {
        // expected
      }
    });

    expect(queryClient.getQueryData(["categories"])).toEqual([category(1), category(2)]);
  });

  it("keeps an optimistically deleted category removed on success", async () => {
    mockDeleteCategory.mockResolvedValue(undefined);
    const { queryClient, wrapper } = makeWrapper();
    queryClient.setQueryData(["categories"], [category(1), category(2)]);

    const { result } = renderHook(() => useDeleteCategory(), { wrapper });
    await act(async () => {
      await result.current.mutateAsync(1);
    });

    expect(queryClient.getQueryData(["categories"])).toEqual([category(2)]);
  });
});
