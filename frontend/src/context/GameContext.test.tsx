import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GameProvider } from "./GameContext";
import { useGame } from "../hooks/useGame";
import { useBootstrapGameData } from "../hooks/useBootstrapGameData";
import { useAuth } from "./AuthContext";
import { apiFetch } from "../utils/api";
import type { ActivityTimerReturn, Player } from "../types";

vi.mock("../hooks/useBootstrapGameData", () => ({
  useBootstrapGameData: vi.fn(),
}));

vi.mock("./AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("../hooks/useActivityTimer", () => ({
  default: vi.fn(),
}));

const mockedUseBootstrapGameData = useBootstrapGameData as ReturnType<typeof vi.fn>;
const mockedUseAuth = useAuth as ReturnType<typeof vi.fn>;
const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

const baseBootstrap = {
  player: null,
  character: null,
  activityTimerInfo: null,
  populationCentreInfo: null,
  xpMods: [],
  loginState: "none" as const,
  loginStreak: 0,
  loginEventAt: null,
  loginRewardXp: 0,
  announcementUnreadCount: 0,
  loading: false,
  error: null,
  buildNumber: "abc123",
  freeTimerLimitSeconds: 1800,
  gameSettings: null,
  onlineCount: 0,
};

const baseActivityTimer: ActivityTimerReturn = {
  status: "empty",
  elapsed: 0,
  duration: 0,
  limitSeconds: null,
  limitReached: false,
  canResume: false,
  autoStopCompletion: null,
  currentActivity: null,
  startActivity: vi.fn(),
  labelActivity: vi.fn(),
  resume: vi.fn(),
  discard: vi.fn(),
  stop: vi.fn(),
  loadFromServer: vi.fn(),
} as unknown as ActivityTimerReturn;

function Consumer() {
  const { player, loginState, buildNumber } = useGame();
  return (
    <div>
      <span data-testid="player">{player ? player.id : "no-player"}</span>
      <span data-testid="login-state">{loginState}</span>
      <span data-testid="build-number">{String(buildNumber)}</span>
    </div>
  );
}

function renderProvider() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <GameProvider>
        <Consumer />
      </GameProvider>
    </QueryClientProvider>
  );
}

describe("GameProvider", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders a loading state while bootstrap data is loading", async () => {
    mockedUseBootstrapGameData.mockReturnValue({ ...baseBootstrap, loading: true });
    mockedUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const activityTimerModule = await import("../hooks/useActivityTimer");
    vi.mocked(activityTimerModule.default).mockReturnValue(baseActivityTimer);

    renderProvider();

    expect(screen.getByText("Loading game data...")).toBeInTheDocument();
  });

  it("renders an error state when bootstrap fails", async () => {
    mockedUseBootstrapGameData.mockReturnValue({
      ...baseBootstrap,
      error: "Something went wrong while loading game data.",
    });
    mockedUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const activityTimerModule = await import("../hooks/useActivityTimer");
    vi.mocked(activityTimerModule.default).mockReturnValue(baseActivityTimer);

    renderProvider();

    expect(
      screen.getByText("Error loading game: Something went wrong while loading game data.")
    ).toBeInTheDocument();
  });

  it("renders children with bootstrap-provided context values once loaded", async () => {
    mockedUseBootstrapGameData.mockReturnValue({ ...baseBootstrap, loginState: "streak" });
    mockedUseAuth.mockReturnValue({ isAuthenticated: false, loading: false });
    const activityTimerModule = await import("../hooks/useActivityTimer");
    vi.mocked(activityTimerModule.default).mockReturnValue(baseActivityTimer);

    renderProvider();

    expect(screen.getByTestId("player")).toHaveTextContent("no-player");
    expect(screen.getByTestId("login-state")).toHaveTextContent("streak");
    expect(screen.getByTestId("build-number")).toHaveTextContent("abc123");
  });

  it("fetches player/character and activities once auth resolves as authenticated", async () => {
    mockedUseBootstrapGameData.mockReturnValue(baseBootstrap);
    mockedUseAuth.mockReturnValue({ isAuthenticated: true, loading: false });
    const activityTimerModule = await import("../hooks/useActivityTimer");
    vi.mocked(activityTimerModule.default).mockReturnValue(baseActivityTimer);
    const player = { id: 1 } as Player;
    mockedApiFetch.mockImplementation((path: string) => {
      if (path.includes("/me/player/")) return Promise.resolve(player);
      if (path.includes("player-activities")) return Promise.resolve({ results: [] });
      if (path.includes("character-activities")) return Promise.resolve({ results: [] });
      return Promise.resolve({});
    });

    renderProvider();

    await waitFor(() => {
      expect(mockedApiFetch).toHaveBeenCalledWith("/me/player/");
    });
    expect(screen.getByTestId("player")).toHaveTextContent("1");
  });

  it("does not fetch player/character while auth is still loading", async () => {
    mockedUseBootstrapGameData.mockReturnValue(baseBootstrap);
    mockedUseAuth.mockReturnValue({ isAuthenticated: false, loading: true });
    const activityTimerModule = await import("../hooks/useActivityTimer");
    vi.mocked(activityTimerModule.default).mockReturnValue(baseActivityTimer);

    renderProvider();

    expect(mockedApiFetch).not.toHaveBeenCalledWith("/me/player/");
  });
});

describe("useGame", () => {
  it("throws when used outside a GameProvider", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    function BareConsumer() {
      useGame();
      return null;
    }

    expect(() => render(<BareConsumer />)).toThrow(
      "useGame must be used within a GameProvider"
    );

    consoleErrorSpy.mockRestore();
  });
});
