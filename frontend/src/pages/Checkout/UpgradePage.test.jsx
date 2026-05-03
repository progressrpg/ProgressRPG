import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import UpgradePage from "./UpgradePage";

const mockUseGame = vi.fn();
const mockUseAppConfig = vi.fn();
const mockApiFetch = vi.fn();

vi.mock("../../context/GameContext", () => ({
  useGame: () => mockUseGame(),
}));

vi.mock("../../hooks/useAppConfig", () => ({
  useAppConfig: () => mockUseAppConfig(),
}));

vi.mock("../../utils/api", () => ({
  apiFetch: (...args) => mockApiFetch(...args),
}));

function renderUpgradePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <UpgradePage />
    </QueryClientProvider>
  );
}

describe("UpgradePage", () => {
  beforeEach(() => {
    mockUseGame.mockReturnValue({
      player: { is_premium: false },
    });
    mockUseAppConfig.mockReturnValue({
      data: { stripe_live_mode: true },
    });
    mockApiFetch.mockReset();
  });

  it("shows only the monthly option", () => {
    renderUpgradePage();

    expect(screen.getByRole("heading", { name: "Premium benefits" })).toBeInTheDocument();
    expect(screen.getByText("Double XP on all activity rewards.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Premium membership" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Monthly" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Annual" })).not.toBeInTheDocument();
    expect(screen.queryByText(/You selected Monthly/i)).not.toBeInTheDocument();
  });

  it("submits checkout with the monthly plan", async () => {
    const user = userEvent.setup();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    mockApiFetch.mockResolvedValue({});

    renderUpgradePage();

    await user.click(screen.getByRole("button", { name: "Go to checkout" }));

    expect(mockApiFetch).toHaveBeenCalledWith("/payments/create-checkout-session/", {
      method: "POST",
      body: JSON.stringify({ plan: "monthly" }),
    });

    consoleErrorSpy.mockRestore();
  });
});
