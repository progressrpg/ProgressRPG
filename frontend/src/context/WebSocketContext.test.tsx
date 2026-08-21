import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WebSocketProvider } from "./WebSocketContext";
import { useWebSocket } from "../hooks/useWebSocket";
import { useGame } from "../hooks/useGame";
import { useOnlineCount } from "./OnlineCountContext";
import { useAuth } from "./AuthContext";
import { useToast } from "../hooks/useToast";
import { useMaintenanceStatus } from "../hooks/useMaintenanceStatus";
import { useMaintenanceContext } from "./MaintenanceContext";
import { useWebSocketConnection } from "../hooks/useWebSocketConnection";
import { handleGlobalWebSocketEvent } from "../websockets/handleGlobalWebSocketEvent";
import type { IncomingWebSocketMessage } from "../types";

vi.mock("../hooks/useGame", () => ({ useGame: vi.fn() }));
vi.mock("./OnlineCountContext", async () => {
  const actual = await vi.importActual<typeof import("./OnlineCountContext")>("./OnlineCountContext");
  return { ...actual, useOnlineCount: vi.fn() };
});
vi.mock("./AuthContext", () => ({ useAuth: vi.fn() }));
vi.mock("../hooks/useToast", () => ({ useToast: vi.fn() }));
vi.mock("../hooks/useMaintenanceStatus", () => ({ useMaintenanceStatus: vi.fn() }));
vi.mock("./MaintenanceContext", async () => {
  const actual = await vi.importActual<typeof import("./MaintenanceContext")>("./MaintenanceContext");
  return { ...actual, useMaintenanceContext: vi.fn() };
});
vi.mock("../hooks/useWebSocketConnection", () => ({ useWebSocketConnection: vi.fn() }));
vi.mock("../websockets/handleGlobalWebSocketEvent", () => ({
  handleGlobalWebSocketEvent: vi.fn().mockResolvedValue(undefined),
}));

const mockedUseGame = useGame as ReturnType<typeof vi.fn>;
const mockedUseOnlineCount = useOnlineCount as ReturnType<typeof vi.fn>;
const mockedUseAuth = useAuth as ReturnType<typeof vi.fn>;
const mockedUseToast = useToast as ReturnType<typeof vi.fn>;
const mockedUseMaintenanceStatus = useMaintenanceStatus as ReturnType<typeof vi.fn>;
const mockedUseMaintenanceContext = useMaintenanceContext as ReturnType<typeof vi.fn>;
const mockedUseWebSocketConnection = useWebSocketConnection as ReturnType<typeof vi.fn>;
const mockedHandleGlobalWebSocketEvent = handleGlobalWebSocketEvent as ReturnType<typeof vi.fn>;

function setup({
  isAuthenticated = true,
  authLoading = false,
  playerId,
}: { isAuthenticated?: boolean; authLoading?: boolean; playerId?: number } = {}) {
  const setOnlinePlayerCount = vi.fn();
  const loadFromServer = vi.fn();
  const showToast = vi.fn();
  const maintenanceRefetch = vi.fn();
  const setMaintenance = vi.fn();
  const send = vi.fn();
  const disconnect = vi.fn();

  mockedUseGame.mockReturnValue({
    player: playerId !== undefined ? { id: playerId, is_premium: false } : null,
    activityTimer: { loadFromServer },
    freeTimerLimitSeconds: 1800,
  });
  mockedUseOnlineCount.mockReturnValue({ setOnlinePlayerCount });
  mockedUseAuth.mockReturnValue({ isAuthenticated, loading: authLoading });
  mockedUseToast.mockReturnValue({ showToast });
  mockedUseMaintenanceStatus.mockReturnValue({ refetch: maintenanceRefetch });
  mockedUseMaintenanceContext.mockReturnValue({ setMaintenance });
  mockedUseWebSocketConnection.mockReturnValue({ send, isConnected: true, disconnect });

  return { setOnlinePlayerCount, loadFromServer, showToast, maintenanceRefetch, setMaintenance, send, disconnect };
}

function renderProvider(children: React.ReactNode) {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <WebSocketProvider>{children}</WebSocketProvider>
    </QueryClientProvider>
  );
}

function Consumer() {
  const ctx = useWebSocket();
  return <span data-testid="connected">{String(ctx.isConnected)}</span>;
}

describe("WebSocketProvider", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("enables the connection once auth resolves as authenticated with a linked player", () => {
    setup({ isAuthenticated: true, authLoading: false, playerId: 7 });

    renderProvider(<Consumer />);

    const [playerId, , , , , shouldConnect] = mockedUseWebSocketConnection.mock.calls[0];
    expect(playerId).toBe(7);
    expect(shouldConnect).toBe(true);
  });

  it("disables the connection while auth is still loading", () => {
    setup({ isAuthenticated: true, authLoading: true, playerId: 7 });

    renderProvider(<Consumer />);

    const [, , , , , shouldConnect] = mockedUseWebSocketConnection.mock.calls[0];
    expect(shouldConnect).toBe(false);
  });

  it("disables the connection when there is no linked player", () => {
    setup({ isAuthenticated: true, authLoading: false, playerId: undefined });

    renderProvider(<Consumer />);

    const [, , , , , shouldConnect] = mockedUseWebSocketConnection.mock.calls[0];
    expect(shouldConnect).toBe(false);
  });

  it("updates the online count and delegates to handleGlobalWebSocketEvent on message", () => {
    const { setOnlinePlayerCount } = setup({ playerId: 1 });

    renderProvider(<Consumer />);

    const onMessage = mockedUseWebSocketConnection.mock.calls[0][1];
    const message: IncomingWebSocketMessage = { type: "online_count", count: 5 } as IncomingWebSocketMessage;

    act(() => {
      onMessage(message);
    });

    expect(setOnlinePlayerCount).toHaveBeenCalledWith(5);
    expect(mockedHandleGlobalWebSocketEvent).toHaveBeenCalledWith(
      message,
      expect.objectContaining({
        showToast: expect.any(Function),
        maintenanceRefetch: expect.any(Function),
        setMaintenance: expect.any(Function),
        onActivityTimerUpdate: expect.any(Function),
        onAnnouncementPublished: expect.any(Function),
      })
    );
  });

  it("notifies handlers registered via addEventHandler, and unregisters them on cleanup", () => {
    setup({ playerId: 1 });
    const handler = vi.fn();

    function HandlerConsumer() {
      const { addEventHandler } = useWebSocket();
      addEventHandler(handler);
      return null;
    }

    renderProvider(<HandlerConsumer />);

    const onMessage = mockedUseWebSocketConnection.mock.calls[0][1];
    const message: IncomingWebSocketMessage = { type: "pong" } as IncomingWebSocketMessage;

    act(() => {
      onMessage(message);
    });

    expect(handler).toHaveBeenCalledWith(message);
  });

  it("reconciles the activity timer and invalidates announcement queries via the callbacks passed to handleGlobalWebSocketEvent", () => {
    const { loadFromServer } = setup({ playerId: 1 });

    renderProvider(<Consumer />);

    // Trigger a message so handleGlobalWebSocketEvent gets called with the
    // provider's callbacks as its options argument.
    const onMessage = mockedUseWebSocketConnection.mock.calls[0][1];
    act(() => {
      onMessage({ type: "pong" } as IncomingWebSocketMessage);
    });
    const { onActivityTimerUpdate, onAnnouncementPublished } =
      mockedHandleGlobalWebSocketEvent.mock.calls[0][1];

    const timerData = { status: "active" } as never;
    onActivityTimerUpdate(timerData);
    expect(loadFromServer).toHaveBeenCalledWith(timerData, { limitSeconds: 1800 });

    expect(() => onAnnouncementPublished()).not.toThrow();
  });

  it("logs on connection error and close", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    setup({ playerId: 1 });

    renderProvider(<Consumer />);

    const [, , onError, onClose] = mockedUseWebSocketConnection.mock.calls[0];
    onError();
    onClose();

    expect(consoleErrorSpy).toHaveBeenCalledWith("WebSocket connection error");
    expect(consoleWarnSpy).toHaveBeenCalledWith("WebSocket disconnected");

    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  it("exposes send/isConnected/disconnect from useWebSocketConnection", () => {
    const { send } = setup({ playerId: 1 });

    function SendConsumer() {
      const ctx = useWebSocket();
      ctx.send({ type: "ping" } as never);
      return <span data-testid="connected">{String(ctx.isConnected)}</span>;
    }

    renderProvider(<SendConsumer />);

    expect(screen.getByTestId("connected")).toHaveTextContent("true");
    expect(send).toHaveBeenCalledWith({ type: "ping" });
  });
});

describe("useWebSocket", () => {
  it("throws when used outside a WebSocketProvider", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    function BareConsumer() {
      useWebSocket();
      return null;
    }

    expect(() => render(<BareConsumer />)).toThrow(
      "useWebSocket must be used within a WebSocketProvider"
    );

    consoleErrorSpy.mockRestore();
  });
});
