import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useDailyGoals, useDeleteAccount, useDownloadUserData, useUpdatePlayer } from "./usePlayer";

const mockUseAuth = vi.fn();
const mockNavigate = vi.fn();
const mockFetchDailyGoals = vi.fn();
const mockUpdatePlayer = vi.fn();
const mockDownloadUserData = vi.fn();
const mockDeleteAccount = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock("../api/player", () => ({
  fetchDailyGoals: () => mockFetchDailyGoals(),
  updatePlayer: (...args: unknown[]) => mockUpdatePlayer(...args),
  downloadUserData: (...args: unknown[]) => mockDownloadUserData(...args),
  deleteAccount: (...args: unknown[]) => mockDeleteAccount(...args),
}));

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

describe("useDailyGoals", () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
    mockFetchDailyGoals.mockReset();
  });

  it("does not fetch when the user is not authenticated", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
    const { wrapper } = makeWrapper();

    renderHook(() => useDailyGoals(), { wrapper });

    expect(mockFetchDailyGoals).not.toHaveBeenCalled();
  });

  it("fetches daily goals when authenticated", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    mockFetchDailyGoals.mockResolvedValue({ completed: 2, target: 5 });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useDailyGoals(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ completed: 2, target: 5 });
  });
});

describe("useUpdatePlayer", () => {
  beforeEach(() => {
    mockUpdatePlayer.mockReset();
  });

  it("invalidates the user query on success", async () => {
    mockUpdatePlayer.mockResolvedValue({ id: 1 });
    const { queryClient, wrapper } = makeWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdatePlayer(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ name: "New" });
    });

    expect(mockUpdatePlayer).toHaveBeenCalledWith({ name: "New" }, expect.anything());
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["user"] });
  });
});

describe("useDownloadUserData", () => {
  it("calls downloadUserData via mutate", async () => {
    mockDownloadUserData.mockResolvedValue({ url: "http://example.com/data.zip" });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useDownloadUserData(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync(undefined);
    });

    expect(mockDownloadUserData).toHaveBeenCalled();
  });
});

describe("useDeleteAccount", () => {
  beforeEach(() => {
    mockDeleteAccount.mockReset();
    mockNavigate.mockReset();
    localStorage.setItem("leftover", "1");
    sessionStorage.setItem("leftover", "1");
  });

  it("clears storage and navigates home on success", async () => {
    mockDeleteAccount.mockResolvedValue(undefined);
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useDeleteAccount(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync(undefined);
    });

    expect(localStorage.getItem("leftover")).toBeNull();
    expect(sessionStorage.getItem("leftover")).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });
});
