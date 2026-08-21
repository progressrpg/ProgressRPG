import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import usePasswordReset from "./usePasswordReset";

function jsonResponse(body: unknown, ok = true) {
  return { ok, json: async () => body } as unknown as Response;
}

describe("usePasswordReset", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  describe("requestPasswordReset", () => {
    it("returns a default success message when the server omits detail", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({})));

      const { result } = renderHook(() => usePasswordReset());
      let out;
      await act(async () => {
        out = await result.current.requestPasswordReset("a@b.com");
      });

      expect(out).toEqual({
        success: true,
        message: "If an account exists for that email, a password reset link has been sent.",
      });
    });

    it("uses the server-provided detail message on success", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Check your inbox" })));

      const { result } = renderHook(() => usePasswordReset());
      let out;
      await act(async () => {
        out = await result.current.requestPasswordReset("a@b.com");
      });

      expect(out).toEqual({ success: true, message: "Check your inbox" });
    });

    it("returns an extracted error message when the response is not ok", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Too many requests" }, false)));

      const { result } = renderHook(() => usePasswordReset());
      let out;
      await act(async () => {
        out = await result.current.requestPasswordReset("a@b.com");
      });

      expect(out).toEqual({
        success: false,
        errors: { detail: "Too many requests" },
        errorMessage: "Too many requests",
      });
    });

    it("returns a generic error when the request throws", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

      const { result } = renderHook(() => usePasswordReset());
      let out;
      await act(async () => {
        out = await result.current.requestPasswordReset("a@b.com");
      });

      expect(out).toEqual({
        success: false,
        errors: null,
        errorMessage: "Unable to send a reset link right now.",
      });
    });
  });

  describe("confirmPasswordReset", () => {
    it("returns a default success message when the server omits detail", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({})));

      const { result } = renderHook(() => usePasswordReset());
      let out;
      await act(async () => {
        out = await result.current.confirmPasswordReset({
          uid: "u1",
          token: "t1",
          password1: "pw",
          password2: "pw",
        });
      });

      expect(out).toEqual({ success: true, message: "Your password has been reset successfully." });
    });

    it("returns an extracted error message when the response is not ok", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ token: ["Invalid token"] }, false)));

      const { result } = renderHook(() => usePasswordReset());
      let out;
      await act(async () => {
        out = await result.current.confirmPasswordReset({
          uid: "u1",
          token: "bad",
          password1: "pw",
          password2: "pw",
        });
      });

      expect(out).toEqual({
        success: false,
        errors: { token: ["Invalid token"] },
        errorMessage: "Invalid token",
      });
    });

    it("returns a generic error when the request throws", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

      const { result } = renderHook(() => usePasswordReset());
      let out;
      await act(async () => {
        out = await result.current.confirmPasswordReset({
          uid: "u1",
          token: "t1",
          password1: "pw",
          password2: "pw",
        });
      });

      expect(out).toEqual({
        success: false,
        errors: null,
        errorMessage: "Unable to reset your password.",
      });
    });
  });
});
