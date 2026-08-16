import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useFeatureFlag } from "./useFeatureFlag";

const mockUseGame = vi.fn();
const mockUseAppConfig = vi.fn();

vi.mock("./useGame", () => ({
  useGame: () => mockUseGame(),
}));

vi.mock("./useAppConfig", () => ({
  useAppConfig: () => mockUseAppConfig(),
}));

function setup({
  player = null,
  featureFlags,
}: {
  player?: { is_premium?: boolean; is_tester?: boolean } | null;
  featureFlags?: Record<string, unknown>;
} = {}) {
  mockUseGame.mockReturnValue({ player });
  mockUseAppConfig.mockReturnValue({
    data: featureFlags ? { feature_flags: featureFlags } : undefined,
  });
}

describe("useFeatureFlag", () => {
  beforeEach(() => {
    mockUseGame.mockReset();
    mockUseAppConfig.mockReset();
  });

  it("grants access when a flag targets the 'all' group", () => {
    setup({ featureFlags: { tasksFeature: ["all"] } });

    const { result } = renderHook(() => useFeatureFlag("tasksFeature"));

    expect(result.current).toBe(true);
  });

  it("grants premium-gated flags only to premium players", () => {
    setup({ player: { is_premium: true }, featureFlags: { tasksFeature: ["premium"] } });
    expect(renderHook(() => useFeatureFlag("tasksFeature")).result.current).toBe(true);

    setup({ player: { is_premium: false }, featureFlags: { tasksFeature: ["premium"] } });
    expect(renderHook(() => useFeatureFlag("tasksFeature")).result.current).toBe(false);
  });

  it("grants tester-gated flags only to testers", () => {
    setup({ player: { is_tester: true }, featureFlags: { tasksFeature: ["testers"] } });
    expect(renderHook(() => useFeatureFlag("tasksFeature")).result.current).toBe(true);

    setup({ player: { is_tester: false }, featureFlags: { tasksFeature: ["testers"] } });
    expect(renderHook(() => useFeatureFlag("tasksFeature")).result.current).toBe(false);
  });

  it("resolves any matching group when several are targeted", () => {
    setup({ player: { is_tester: true }, featureFlags: { tasksFeature: ["premium", "testers"] } });

    expect(renderHook(() => useFeatureFlag("tasksFeature")).result.current).toBe(true);
  });

  it("denies access when a flag targets no groups", () => {
    setup({ player: { is_premium: true }, featureFlags: { tasksFeature: [] } });

    expect(renderHook(() => useFeatureFlag("tasksFeature")).result.current).toBe(false);
  });

  it("falls back to the bundled defaults when the remote config omits the flag", () => {
    // No appConfig at all -> uses local featureFlags (tasksFeature: ['testers']).
    setup({ player: { is_tester: true } });

    expect(renderHook(() => useFeatureFlag("tasksFeature")).result.current).toBe(true);
  });

  it("prefers the remote config over the bundled default", () => {
    // Remote disables a flag that the bundled default would have enabled.
    setup({ player: { is_premium: false }, featureFlags: { tasksFeature: ["premium"] } });

    expect(renderHook(() => useFeatureFlag("tasksFeature")).result.current).toBe(false);
  });
});
