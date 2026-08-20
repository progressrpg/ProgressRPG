import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import useWaitlistJoin from "./useWaitlistJoin";

function jsonResponse(body: unknown, ok = true) {
  return { ok, json: async () => body } as unknown as Response;
}

describe("useWaitlistJoin", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns a default success message when the server omits one", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({})));

    const { result } = renderHook(() => useWaitlistJoin());
    let out;
    await act(async () => {
      out = await result.current.joinWaitlist("a@b.com");
    });

    expect(out).toEqual({ success: true, message: "You're on the waitlist." });
  });

  it("returns an extracted error message when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Already joined" }, false)));

    const { result } = renderHook(() => useWaitlistJoin());
    let out;
    await act(async () => {
      out = await result.current.joinWaitlist("a@b.com");
    });

    expect(out).toEqual({ success: false, errorMessage: "Already joined" });
  });

  it("returns a generic error when the request throws", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    const { result } = renderHook(() => useWaitlistJoin());
    let out;
    await act(async () => {
      out = await result.current.joinWaitlist("a@b.com");
    });

    expect(out).toEqual({
      success: false,
      errorMessage: "Unable to join the waitlist right now. Please try again later.",
    });
  });
});
