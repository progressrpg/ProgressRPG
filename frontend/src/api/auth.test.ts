import { describe, expect, it, vi } from "vitest";

import { loginUser } from "./auth";
import { apiFetch } from "../utils/api";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

describe("loginUser", () => {
  it("posts credentials to the JWT create endpoint via apiFetch with skipAuth", async () => {
    (apiFetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      access_token: "a",
      refresh_token: "r",
    });

    const result = await loginUser("alice", "hunter2");

    expect(apiFetch).toHaveBeenCalledWith("/auth/jwt/create/", {
      method: "POST",
      body: JSON.stringify({ username: "alice", password: "hunter2" }),
      skipAuth: true,
    });
    expect(result).toEqual({ access_token: "a", refresh_token: "r" });
  });

  it("propagates a rejected login (401) as-is", async () => {
    const error = new Error("rejected");
    (apiFetch as ReturnType<typeof vi.fn>).mockRejectedValue(error);

    await expect(loginUser("alice", "wrong")).rejects.toThrow("rejected");
  });
});
