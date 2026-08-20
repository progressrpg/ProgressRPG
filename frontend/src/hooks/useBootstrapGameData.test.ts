import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useBootstrapGameData } from "./useBootstrapGameData";

const mockUseAuth = vi.fn();
const mockApiFetch = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../utils/api", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

describe("useBootstrapGameData", () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
    mockApiFetch.mockReset();
  });

  it("stays loading while auth is still resolving, without fetching", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: true });

    const { result } = renderHook(() => useBootstrapGameData());

    expect(result.current.loading).toBe(true);
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  it("resets to logged-out defaults when not authenticated", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });

    const { result } = renderHook(() => useBootstrapGameData());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.loginState).toBe("none");
    expect(result.current.loginStreak).toBe(0);
    expect(result.current.loginEventAt).toBeNull();
    expect(result.current.loginRewardXp).toBe(0);
    expect(mockApiFetch).not.toHaveBeenCalled();
  });

  it("populates game data from /fetch_info/ when authenticated", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    mockApiFetch.mockResolvedValue({
      player: { id: 1 },
      character: { id: 2 },
      activity_timer: { id: 3 },
      population_centre: { id: 4 },
      xp_mods: [{ id: 5 }],
      login_state: "streak",
      login_streak: "7",
      login_event_at: "2026-01-01T00:00:00Z",
      login_reward_xp: "50",
      announcement_unread_count: "2",
      build_number: "abc123",
      game_settings: { free_timer_limit_seconds: 900 },
      online_count: "12",
    });

    const { result } = renderHook(() => useBootstrapGameData());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(mockApiFetch).toHaveBeenCalledWith("/fetch_info/");
    expect(result.current.player).toEqual({ id: 1 });
    expect(result.current.character).toEqual({ id: 2 });
    expect(result.current.loginState).toBe("streak");
    expect(result.current.loginStreak).toBe(7);
    expect(result.current.loginRewardXp).toBe(50);
    expect(result.current.announcementUnreadCount).toBe(2);
    expect(result.current.onlineCount).toBe(12);
    expect(result.current.freeTimerLimitSeconds).toBe(900);
    expect(result.current.error).toBeNull();
  });

  it("falls back to the top-level free timer limit when game_settings omits it", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    mockApiFetch.mockResolvedValue({
      player: null,
      character: null,
      activity_timer: null,
      population_centre: null,
      free_timer_limit_seconds: 600,
    });

    const { result } = renderHook(() => useBootstrapGameData());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.freeTimerLimitSeconds).toBe(600);
  });

  it("uses the default free timer limit when neither source provides one", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    mockApiFetch.mockResolvedValue({ player: null, character: null, activity_timer: null, population_centre: null });

    const { result } = renderHook(() => useBootstrapGameData());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.freeTimerLimitSeconds).toBe(1800);
  });

  it("sets an error and stops loading when the fetch fails", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    mockApiFetch.mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => useBootstrapGameData());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toBe("Something went wrong while loading game data.");
  });
});
