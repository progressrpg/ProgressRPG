import { act, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "./AuthContext";
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
