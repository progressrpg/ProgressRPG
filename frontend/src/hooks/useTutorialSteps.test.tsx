import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useTutorialSteps from "./useTutorialSteps";

const mockApiFetch = vi.fn();

vi.mock("../utils/api", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return wrapper;
}

describe("useTutorialSteps", () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
  });

  it("returns a plain array response as-is", async () => {
    mockApiFetch.mockResolvedValue([{ id: 1 }, { id: 2 }]);
    const wrapper = makeWrapper();

    const { result } = renderHook(() => useTutorialSteps(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.steps).toEqual([{ id: 1 }, { id: 2 }]);
  });

  it("unwraps a paginated response's results", async () => {
    mockApiFetch.mockResolvedValue({ results: [{ id: 3 }] });
    const wrapper = makeWrapper();

    const { result } = renderHook(() => useTutorialSteps(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.steps).toEqual([{ id: 3 }]);
  });

  it("defaults to an empty array when the paginated response has no results", async () => {
    mockApiFetch.mockResolvedValue({});
    const wrapper = makeWrapper();

    const { result } = renderHook(() => useTutorialSteps(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.steps).toEqual([]);
  });
});
