import { afterEach, describe, expect, it, vi } from "vitest";

import { completeOnboarding } from "./onboarding";
import { apiFetch } from "../utils/api";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("completeOnboarding", () => {
  it("posts to the complete_onboarding endpoint", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await completeOnboarding();

    expect(mockedApiFetch).toHaveBeenCalledWith("/me/complete_onboarding/", {
      method: "POST",
    });
  });
});
