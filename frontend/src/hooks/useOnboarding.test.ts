import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useOnboarding from "./useOnboarding";

const mockUseGame = vi.fn();
const mockApiFetch = vi.fn();

vi.mock("./useGame", () => ({
  useGame: () => mockUseGame(),
}));

vi.mock("../utils/api", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

describe("useOnboarding", () => {
  const fetchPlayerAndCharacter = vi.fn();

  beforeEach(() => {
    mockApiFetch.mockReset();
    fetchPlayerAndCharacter.mockReset();
  });

  it("is undefined when there is no player yet", () => {
    mockUseGame.mockReturnValue({ player: null, loading: true, fetchPlayerAndCharacter });

    const { result } = renderHook(() => useOnboarding());

    expect(result.current.completed).toBeUndefined();
  });

  it("reflects the player's onboarding_completed flag", () => {
    mockUseGame.mockReturnValue({ player: { onboarding_completed: true }, loading: false, fetchPlayerAndCharacter });

    const { result } = renderHook(() => useOnboarding());

    expect(result.current.completed).toBe(true);
  });

  it("posts to complete onboarding and refetches player data on success", async () => {
    mockUseGame.mockReturnValue({ player: { onboarding_completed: false }, loading: false, fetchPlayerAndCharacter });
    mockApiFetch.mockResolvedValue(undefined);
    fetchPlayerAndCharacter.mockResolvedValue(undefined);

    const { result } = renderHook(() => useOnboarding());

    let success;
    await act(async () => {
      success = await result.current.completeOnboarding();
    });

    expect(mockApiFetch).toHaveBeenCalledWith("/me/complete_onboarding/", { method: "POST" });
    expect(fetchPlayerAndCharacter).toHaveBeenCalled();
    expect(success).toBe(true);
    expect(result.current.error).toBe("");
  });

  it("sets an error message and returns false when the request fails", async () => {
    mockUseGame.mockReturnValue({ player: { onboarding_completed: false }, loading: false, fetchPlayerAndCharacter });
    mockApiFetch.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useOnboarding());

    let success;
    await act(async () => {
      success = await result.current.completeOnboarding();
    });

    expect(success).toBe(false);
    expect(result.current.error).toBe("boom");
  });

  it("falls back to a generic error message when the thrown error has no message", async () => {
    mockUseGame.mockReturnValue({ player: { onboarding_completed: false }, loading: false, fetchPlayerAndCharacter });
    mockApiFetch.mockRejectedValue(null);

    const { result } = renderHook(() => useOnboarding());

    await act(async () => {
      await result.current.completeOnboarding();
    });

    expect(result.current.error).toBe("Failed to complete onboarding.");
  });
});
