import { describe, expect, it } from "vitest";

import { mockAuthContextValue } from "./mockAuthContext";

describe("mockAuthContextValue", () => {
  it("defaults to a logged-out state with no tokens or user", () => {
    const value = mockAuthContextValue();

    expect(value.isAuthenticated).toBe(false);
    expect(value.accessToken).toBeNull();
    expect(value.refreshToken).toBeNull();
    expect(value.user).toBeNull();
  });

  it("fills in mock tokens and a mock user when authenticated is true", () => {
    const value = mockAuthContextValue({ authenticated: true });

    expect(value.isAuthenticated).toBe(true);
    expect(value.accessToken).toBe("mock-access-token");
    expect(value.refreshToken).toBe("mock-refresh-token");
    expect(value.user).toMatchObject({ email: "demo@example.com" });
  });

  it("applies overrides on top of the authenticated defaults", () => {
    const value = mockAuthContextValue({ authenticated: true, user: { is_staff: true } as never });

    expect(value.isAuthenticated).toBe(true);
    expect(value.user).toEqual({ is_staff: true });
  });

  it("rejects when the unmocked authFetch stub is called", async () => {
    const value = mockAuthContextValue();

    await expect(value.authFetch("/x")).rejects.toThrow("authFetch is not mocked in Storybook");
  });
});
