import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { jwtDecode } from "jwt-decode";

import {
  apiFetch,
  ApiFetchError,
  getValidAccessToken,
  setMaintenanceHandler,
  setNetworkErrorHandler,
  setUnauthorizedHandler,
} from "./api";
import { getStoredAuthTokens, storeAuthTokens } from "./authStorage";

vi.mock("jwt-decode", () => ({
  jwtDecode: vi.fn(),
}));

describe("getValidAccessToken", () => {
  beforeEach(() => {
    storeAuthTokens("expiring-token", "refresh-token", true);
    (jwtDecode as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      exp: Date.now() / 1000 - 10, // already expired
    });
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    setUnauthorizedHandler(null);
    vi.clearAllMocks();
  });

  it("stores the refreshed access token returned as access_token", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: "new-access-token" }),
    });

    const token = await getValidAccessToken();

    expect(token).toBe("new-access-token");
    expect(getStoredAuthTokens().accessToken).toBe("new-access-token");
  });

  it("logs the user out and throws when no tokens are stored at all", async () => {
    localStorage.clear();
    sessionStorage.clear();
    const unauthorizedHandler = vi.fn();
    setUnauthorizedHandler(unauthorizedHandler);

    await expect(getValidAccessToken()).rejects.toThrow("Missing tokens");

    expect(unauthorizedHandler).toHaveBeenCalled();
  });

  it("returns the stored access token without refreshing when it is not expiring soon", async () => {
    storeAuthTokens("fresh-token", "refresh-token", true);
    (jwtDecode as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      exp: Date.now() / 1000 + 3600, // an hour from now
    });

    const token = await getValidAccessToken();

    expect(token).toBe("fresh-token");
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("treats a token that fails to decode as expiring soon and refreshes it", async () => {
    (jwtDecode as unknown as ReturnType<typeof vi.fn>).mockImplementation(() => {
      throw new Error("malformed token");
    });
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: "refreshed-token" }),
    });

    const token = await getValidAccessToken();

    expect(token).toBe("refreshed-token");
  });

  it("logs the user out when the refresh response is missing access_token", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({ access: "unexpected-shape" }),
    });

    const unauthorizedHandler = vi.fn();
    setUnauthorizedHandler(unauthorizedHandler);

    await expect(getValidAccessToken()).rejects.toThrow("Token refresh failed");

    expect(unauthorizedHandler).toHaveBeenCalled();
    expect(getStoredAuthTokens().accessToken).toBeNull();
  });
});

describe("apiFetch", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    setMaintenanceHandler(null);
    setNetworkErrorHandler(null);
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  const okResponse = { ok: true, status: 200, json: async () => ({ ok: true }) };

  it("succeeds on the first attempt with no retry", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okResponse);

    const result = await apiFetch("/me/", {}, "test-token");

    expect(result).toEqual({ ok: true });
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("falls back to getValidAccessToken when no explicit access token is given", async () => {
    storeAuthTokens("stored-access", "stored-refresh", true);
    (jwtDecode as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      exp: Date.now() / 1000 + 3600,
    });
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okResponse);

    await apiFetch("/me/", {});

    const [, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(requestInit.headers.Authorization).toBe("Bearer stored-access");

    localStorage.clear();
    sessionStorage.clear();
  });

  it("recovers after one transient network error", async () => {
    vi.useFakeTimers();
    (globalThis.fetch as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(okResponse);

    const promise = apiFetch("/me/", {}, "test-token");
    await vi.advanceTimersByTimeAsync(300);
    const result = await promise;

    expect(result).toEqual({ ok: true });
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });

  it("recovers after two transient network errors", async () => {
    vi.useFakeTimers();
    (globalThis.fetch as ReturnType<typeof vi.fn>)
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(okResponse);

    const promise = apiFetch("/me/", {}, "test-token");
    await vi.advanceTimersByTimeAsync(300);
    await vi.advanceTimersByTimeAsync(600);
    const result = await promise;

    expect(result).toEqual({ ok: true });
    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });

  it("rejects with a network ApiFetchError once retries are exhausted, without a handler registered", async () => {
    vi.useFakeTimers();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new TypeError("Failed to fetch"));

    const promise = apiFetch("/me/", {}, "test-token");
    const expectation = expect(promise).rejects.toMatchObject({
      kind: "network",
    } satisfies Partial<ApiFetchError>);
    await vi.advanceTimersByTimeAsync(300);
    await vi.advanceTimersByTimeAsync(600);
    await expectation;

    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });

  it("invokes the registered network-error handler once retries are exhausted", async () => {
    vi.useFakeTimers();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new TypeError("Failed to fetch"));
    const networkErrorHandler = vi.fn();
    setNetworkErrorHandler(networkErrorHandler);

    const promise = apiFetch("/me/", {}, "test-token");
    const expectation = expect(promise).rejects.toMatchObject({
      kind: "network",
    } satisfies Partial<ApiFetchError>);
    await vi.advanceTimersByTimeAsync(300);
    await vi.advanceTimersByTimeAsync(600);
    await expectation;

    expect(networkErrorHandler).toHaveBeenCalledTimes(1);
  });

  it("does not retry a non-network error", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("boom"));

    await expect(apiFetch("/me/", {}, "test-token")).rejects.toThrow("boom");

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("does not retry a 401 response", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ok: false, status: 401 });

    await expect(apiFetch("/me/", {}, "test-token")).rejects.toMatchObject({
      kind: "unauthorized",
    } satisfies Partial<ApiFetchError>);

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("does not retry a 503 response, rejecting with a service_unavailable ApiFetchError without a handler registered", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ok: false, status: 503 });

    await expect(apiFetch("/me/", {}, "test-token")).rejects.toMatchObject({
      kind: "service_unavailable",
    } satisfies Partial<ApiFetchError>);

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("invokes the registered maintenance handler on a 503 response", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ok: false, status: 503 });
    const maintenanceHandler = vi.fn();
    setMaintenanceHandler(maintenanceHandler);

    await expect(apiFetch("/me/", {}, "test-token")).rejects.toMatchObject({
      kind: "service_unavailable",
    } satisfies Partial<ApiFetchError>);

    expect(maintenanceHandler).toHaveBeenCalledTimes(1);
  });

  it("throws with the response body text on a non-ok, non-401/503 response", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => "Internal Server Error",
    });

    await expect(apiFetch("/me/", {}, "test-token")).rejects.toThrow("Internal Server Error");
  });

  it("falls back to a generic message when the error response has no body text", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => "",
    });

    await expect(apiFetch("/me/", {}, "test-token")).rejects.toThrow("API error");
  });

  it("returns a Blob when responseType is blob", async () => {
    const blob = new Blob(["data"]);
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      blob: async () => blob,
    });

    const result = await apiFetch("/export/", { responseType: "blob" }, "test-token");

    expect(result).toBe(blob);
  });

  it("returns text when responseType is text", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: async () => "raw text",
    });

    const result = await apiFetch("/export/", { responseType: "text" }, "test-token");

    expect(result).toBe("raw text");
  });

  it("returns the raw Response when responseType is raw", async () => {
    const rawResponse = { ok: true, status: 200 };
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(rawResponse);

    const result = await apiFetch("/export/", { responseType: "raw" }, "test-token");

    expect(result).toBe(rawResponse);
  });

  describe("skipAuth", () => {
    afterEach(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    it("does not attach an Authorization header or call getValidAccessToken", async () => {
      // No tokens in storage at all — getValidAccessToken() would throw if called.
      (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okResponse);

      await apiFetch("/auth/jwt/create/", { method: "POST", skipAuth: true });

      const [, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(requestInit.headers).not.toHaveProperty("Authorization");
    });

    it("rejects with an unauthorized ApiFetchError on 401, without clearing storage or invoking the handler", async () => {
      storeAuthTokens("still-valid-access-token", "still-valid-refresh-token", true);
      (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ok: false, status: 401 });
      const unauthorizedHandler = vi.fn();
      setUnauthorizedHandler(unauthorizedHandler);

      await expect(apiFetch("/auth/jwt/create/", { method: "POST", skipAuth: true })).rejects.toMatchObject({
        kind: "unauthorized",
      } satisfies Partial<ApiFetchError>);

      expect(unauthorizedHandler).not.toHaveBeenCalled();
      // A rejected login shouldn't log out whatever session was already stored.
      expect(getStoredAuthTokens().accessToken).toBe("still-valid-access-token");

      setUnauthorizedHandler(null);
    });

    it("takes priority over an explicitAccessToken — no Authorization header either way", async () => {
      (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(okResponse);

      await apiFetch("/me/", { skipAuth: true }, "explicit-token");

      const [, requestInit] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(requestInit.headers).not.toHaveProperty("Authorization");
    });
  });
});
