import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Account from "./Account";

const mockUseGame = vi.fn();
const mockUpdatePlayer = vi.fn();
const mockDownloadUserData = vi.fn();
const mockDeleteAccount = vi.fn();

vi.mock("../../context/GameContext", () => ({
  useGame: () => mockUseGame(),
}));

vi.mock("../../api/player", () => ({
  updatePlayer: (...args) => mockUpdatePlayer(...args),
  downloadUserData: (...args) => mockDownloadUserData(...args),
  deleteAccount: (...args) => mockDeleteAccount(...args),
}));

function renderAccount() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <Account />
      </QueryClientProvider>
    </MemoryRouter>
  );
}

describe("Account", () => {
  beforeEach(() => {
    mockUpdatePlayer.mockReset();
    mockDownloadUserData.mockReset();
    mockDeleteAccount.mockReset();
    mockUseGame.mockReturnValue({
      player: {
        name: "player_01234",
        level: 3,
        xp: 25,
        xp_next_level: 100,
        total_activities: 4,
        total_time: 5400,
        is_premium: false,
      },
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });
  });

  it("edits the player name inline instead of linking to another page", async () => {
    const user = userEvent.setup();

    renderAccount();

    expect(
      screen.queryByRole("link", { name: /edit name/i })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /edit name/i }));

    expect(screen.getByRole("textbox")).toHaveValue("player_01234");
    expect(screen.getByRole("button", { name: /save name/i })).toBeDisabled();
  });

  it("shows violated name rules and keeps save disabled for invalid input", async () => {
    const user = userEvent.setup();

    renderAccount();

    await user.click(screen.getByRole("button", { name: /edit name/i }));

    const input = screen.getByRole("textbox");
    await user.clear(input);
    await user.type(input, "bad!!name");

    const saveButton = screen.getByRole("button", { name: /save name/i });
    const invalidRule = screen.getByText(/allowed: spaces, hyphens/i);
    const shortRule = screen.getByText(/use 3-20 characters/i);

    expect(saveButton).toBeDisabled();
    expect(invalidRule.className).toMatch(/ruleInvalid/);
    expect(shortRule.className).not.toMatch(/ruleInvalid/);
  });

  it("allows boundary punctuation but rejects too-short names", async () => {
    const user = userEvent.setup();

    renderAccount();

    await user.click(screen.getByRole("button", { name: /edit name/i }));

    const input = screen.getByRole("textbox");
    const saveButton = screen.getByRole("button", { name: /save name/i });

    await user.clear(input);
    await user.type(input, "-A-");
    expect(saveButton).not.toBeDisabled();

    await user.clear(input);
    await user.type(input, "ab");

    const shortRule = screen.getByText(/use 3-20 characters/i);
    expect(saveButton).toBeDisabled();
    expect(shortRule.className).toMatch(/ruleInvalid/);
  });
});
