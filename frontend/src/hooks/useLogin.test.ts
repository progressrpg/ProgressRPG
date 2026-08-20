import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import useLogin from "./useLogin";

function jsonResponse(body: unknown, { ok = true, status = 200, url = "http://localhost:8000/api/v1/auth/jwt/create/" } = {}) {
  const text = JSON.stringify(body);
  return {
    ok,
    status,
    url,
    headers: { get: () => "application/json" },
    text: async () => text,
  } as unknown as Response;
}

describe("useLogin", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns tokens on a successful login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ access_token: "access-1", refresh_token: "refresh-1" }))
    );

    const { result } = renderHook(() => useLogin());

    let loginResult;
    await act(async () => {
      loginResult = await result.current("a@b.com", "pw");
    });

    expect(loginResult).toEqual({
      success: true,
      tokens: { access_token: "access-1", refresh_token: "refresh-1" },
    });
  });

  it("accepts the access/refresh field aliases", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ access: "access-2", refresh: "refresh-2" })));

    const { result } = renderHook(() => useLogin());

    let loginResult;
    await act(async () => {
      loginResult = await result.current("a@b.com", "pw");
    });

    expect(loginResult).toEqual({
      success: true,
      tokens: { access_token: "access-2", refresh_token: "refresh-2" },
    });
  });

  it("fails with a generic message when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        url: "http://localhost:8000/api/v1/auth/jwt/create/",
        headers: { get: () => "application/json" },
        text: async () => "bad request",
      } as unknown as Response)
    );

    const { result } = renderHook(() => useLogin());

    let loginResult;
    await act(async () => {
      loginResult = await result.current("a@b.com", "pw");
    });

    expect(loginResult).toEqual({ success: false, error: "Login failed. Please try again." });
  });

  it("fails with a specific message when the server reports no active account", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        url: "http://localhost:8000/api/v1/auth/jwt/create/",
        headers: { get: () => "application/json" },
        text: async () => "No active account found with the given credentials",
      } as unknown as Response)
    );

    const { result } = renderHook(() => useLogin());

    let loginResult;
    await act(async () => {
      loginResult = await result.current("a@b.com", "wrong-pw");
    });

    expect(loginResult).toEqual({ success: false, error: "Invalid email or password; please try again." });
  });

  it("fails with a server-unavailable message on a network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const { result } = renderHook(() => useLogin());

    let loginResult;
    await act(async () => {
      loginResult = await result.current("a@b.com", "pw");
    });

    expect(loginResult).toEqual({
      success: false,
      error: "The server is unavailable. Please try again in a moment.",
    });
  });

  it("fails when the response body is missing tokens", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({})));

    const { result } = renderHook(() => useLogin());

    let loginResult;
    await act(async () => {
      loginResult = await result.current("a@b.com", "pw");
    });

    expect(loginResult).toEqual({ success: false, error: "Login failed. Please try again." });
  });
});
