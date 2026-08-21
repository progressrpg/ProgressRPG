import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import useWaitlistSignup from "./useWaitlistSignup";

function jsonResponse(body: unknown, ok = true) {
  return { ok, json: async () => body } as unknown as Response;
}

describe("useWaitlistSignup", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns a default success message and null state when the server omits both", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({})));

    const { result } = renderHook(() => useWaitlistSignup());
    let out;
    await act(async () => {
      out = await result.current.requestWaitlistSignup("a@b.com");
    });

    expect(out).toEqual({ success: true, message: "You're on the list! We'll be in touch soon.", state: null });
  });

  it("passes through the server-provided state string", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ state: "pending_confirmation" })));

    const { result } = renderHook(() => useWaitlistSignup());
    let out;
    await act(async () => {
      out = await result.current.requestWaitlistSignup("a@b.com");
    });

    expect(out).toMatchObject({ success: true, state: "pending_confirmation" });
  });

  it("returns an extracted error message when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ email: ["Invalid email"] }, false)));

    const { result } = renderHook(() => useWaitlistSignup());
    let out;
    await act(async () => {
      out = await result.current.requestWaitlistSignup("bad");
    });

    expect(out).toEqual({ success: false, errorMessage: "Invalid email" });
  });

  it("returns a generic error when the request throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    const { result } = renderHook(() => useWaitlistSignup());
    let out;
    await act(async () => {
      out = await result.current.requestWaitlistSignup("a@b.com");
    });

    expect(out).toEqual({
      success: false,
      errorMessage: "Unable to join the waitlist right now. Please try again later.",
    });
  });
});
