import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import useRegister from "./useRegister";

const mockLogin = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ login: mockLogin }),
}));

function jsonResponse(body: unknown, ok = true) {
  return { ok, json: async () => body } as unknown as Response;
}

describe("useRegister", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    mockLogin.mockReset();
  });

  const invoke = () =>
    renderHook(() => useRegister());

  it("returns an error with the first non_field_error when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ non_field_errors: ["Email already registered"] }, false))
    );

    const { result } = invoke();
    let registerResult;
    await act(async () => {
      registerResult = await result.current.register(
        "a@b.com", "pw1", "pw1", {}, true, "token", "UTC"
      );
    });

    expect(registerResult).toEqual({
      success: false,
      errors: { non_field_errors: ["Email already registered"] },
      errorMessage: "Email already registered",
    });
  });

  it("falls back to a generic error message when non_field_errors is absent", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({}, false)));

    const { result } = invoke();
    let registerResult;
    await act(async () => {
      registerResult = await result.current.register("a@b.com", "pw1", "pw1", {}, true, "token", "UTC");
    });

    expect(registerResult).toMatchObject({ success: false, errorMessage: "Registration failed." });
  });

  it("tracks character availability from the response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ characters_available: true, detail: "Verification email sent" }))
    );

    const { result } = invoke();
    await act(async () => {
      await result.current.register("a@b.com", "pw1", "pw1", {}, true, "token", "UTC");
    });

    expect(result.current.characterAvailable).toBe(true);
  });

  it("reports confirmation-required when a verification email was sent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Verification email sent to you" }))
    );

    const { result } = invoke();
    let registerResult;
    await act(async () => {
      registerResult = await result.current.register("a@b.com", "pw1", "pw1", {}, true, "token", "UTC");
    });

    expect(registerResult).toEqual({
      success: true,
      confirmationRequired: true,
      message: "Verification email sent to you",
    });
  });

  it("logs in directly when the response includes tokens", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ accessToken: "access-1", refreshToken: "refresh-1" }))
    );
    mockLogin.mockResolvedValue(undefined);

    const { result } = invoke();
    let registerResult;
    await act(async () => {
      registerResult = await result.current.register("a@b.com", "pw1", "pw1", {}, true, "token", "UTC");
    });

    expect(mockLogin).toHaveBeenCalledWith("access-1", "refresh-1", { rememberMe: false });
    expect(registerResult).toEqual({ success: true });
  });

  it("falls back to a generic confirmation message for unexpected success payloads", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ characters_available: false })));

    const { result } = invoke();
    let registerResult;
    await act(async () => {
      registerResult = await result.current.register("a@b.com", "pw1", "pw1", {}, true, "token", "UTC");
    });

    expect(registerResult).toEqual({
      success: true,
      confirmationRequired: true,
      message: "Please check your email to confirm your account.",
      availableCharacters: false,
    });
  });

  it("sends invite_token instead of invite_code when a token is present", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: "Verification email sent" }));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = invoke();
    await act(async () => {
      await result.current.register("a@b.com", "pw1", "pw1", { token: "invite-tok", code: "ignored" }, true, "token", "UTC");
    });

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.invite_token).toBe("invite-tok");
    expect(body.invite_code).toBeUndefined();
  });

  it("returns a generic error when the request throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    const { result } = invoke();
    let registerResult;
    await act(async () => {
      registerResult = await result.current.register("a@b.com", "pw1", "pw1", {}, true, "token", "UTC");
    });

    expect(registerResult).toEqual({
      success: false,
      errors: null,
      errorMessage: "Something went wrong, please try again.",
    });
  });
});
