import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./AuthContext";
import { apiFetch, setUnauthorizedHandler } from "../utils/api";
import { clearAuthStorage, storeAuthTokens } from "../utils/authStorage";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
  ApiFetchError: class ApiFetchError extends Error {
    kind: string;
    constructor(kind: string, message: string) {
      super(message);
      this.kind = kind;
    }
  },
  setUnauthorizedHandler: vi.fn(),
}));

describe("AuthProvider unauthorized-handler registration", () => {
  beforeEach(() => {
    vi.mocked(setUnauthorizedHandler).mockClear();
  });

  afterEach(() => {
    clearAuthStorage();
    localStorage.clear();
    sessionStorage.clear();
  });

  it("registers a handler on mount and clears it on unmount", () => {
    const { unmount } = render(
      <AuthProvider>
        <div />
      </AuthProvider>,
    );

    expect(setUnauthorizedHandler).toHaveBeenCalledTimes(1);
    expect(setUnauthorizedHandler).toHaveBeenCalledWith(expect.any(Function));

    unmount();

    expect(setUnauthorizedHandler).toHaveBeenCalledTimes(2);
    expect(setUnauthorizedHandler).toHaveBeenLastCalledWith(null);
  });

  it("registers a handler that logs the session out", async () => {
    storeAuthTokens("access-token", "refresh-token", true);
    vi.mocked(apiFetch).mockResolvedValueOnce({ id: 1, email: "test@example.com" });

    render(
      <AuthProvider>
        <div />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/me/");
    });

    const registeredHandler = vi.mocked(setUnauthorizedHandler).mock.calls[0][0];
    expect(registeredHandler).toBeInstanceOf(Function);

    act(() => {
      registeredHandler?.();
    });

    expect(localStorage.getItem("authSession")).toBeNull();
  });

  it("each mounted provider unregisters only its own handler on unmount", () => {
    const { unmount: unmountFirst } = render(
      <AuthProvider>
        <div />
      </AuthProvider>,
    );
    const { unmount: unmountSecond } = render(
      <AuthProvider>
        <div />
      </AuthProvider>,
    );

    expect(setUnauthorizedHandler).toHaveBeenCalledTimes(2);

    unmountSecond();
    expect(setUnauthorizedHandler).toHaveBeenLastCalledWith(null);

    unmountFirst();
    expect(setUnauthorizedHandler).toHaveBeenLastCalledWith(null);
    expect(setUnauthorizedHandler).toHaveBeenCalledTimes(4);
  });
});

function Consumer() {
  const { isAuthenticated, user, loading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="user">{user ? user.email : "none"}</span>
      <button onClick={() => login("new-access", "new-refresh", { rememberMe: true })}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

describe("AuthProvider session lifecycle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    clearAuthStorage();
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it("resolves to unauthenticated without calling apiFetch when no tokens are stored", async () => {
    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });
    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("verifies stored tokens on mount and loads the current user", async () => {
    storeAuthTokens("access-token", "refresh-token", true);
    vi.mocked(apiFetch).mockResolvedValueOnce({ id: 1, email: "stored@example.com" });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });
    expect(screen.getByTestId("user")).toHaveTextContent("stored@example.com");
  });

  it("login() stores tokens and loads the user without a duplicate /me/ verification call", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ id: 2, email: "login@example.com" });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });
    expect(screen.getByTestId("user")).toHaveTextContent("login@example.com");
    expect(apiFetch).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem("authSession")).not.toBeNull();
  });

  it("login() leaves the user unauthenticated if fetching /me/ fails", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("network down"));

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });

    await act(async () => {
      screen.getByText("login").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });
    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
  });

  it("logout() clears storage and resets user/token state", async () => {
    storeAuthTokens("access-token", "refresh-token", true);
    vi.mocked(apiFetch).mockResolvedValueOnce({ id: 1, email: "stored@example.com" });

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("authenticated")).toHaveTextContent("true");
    });

    act(() => {
      screen.getByText("logout").click();
    });

    expect(screen.getByTestId("authenticated")).toHaveTextContent("false");
    expect(screen.getByTestId("user")).toHaveTextContent("none");
    expect(localStorage.getItem("authSession")).toBeNull();
  });

  it("does not treat a service-unavailable error during verification as an invalid session", async () => {
    storeAuthTokens("access-token", "refresh-token", true);
    const { ApiFetchError } = await import("../utils/api");
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiFetchError("service_unavailable", "down for maintenance"));

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false");
    });
    // Tokens are untouched by a transient service outage - unlike an actual
    // 401, this doesn't clear the stored session.
    expect(localStorage.getItem("authSession")).not.toBeNull();
  });
});

describe("useAuth", () => {
  it("throws when used outside an AuthProvider", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    function BareConsumer() {
      useAuth();
      return null;
    }

    expect(() => render(<BareConsumer />)).toThrow(
      "useAuth must be used within an AuthProvider",
    );

    consoleErrorSpy.mockRestore();
  });
});
