import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Home from "./Home";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("Home", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
  });

  it("renders the welcome message and CTA", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { name: /welcome to progress rpg/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/embark on epic quests and master your time/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /enter the game/i })).toBeInTheDocument();
  });

  it("navigates to the game when the CTA is clicked", async () => {
    const user = userEvent.setup();

    render(<Home />);
    await user.click(screen.getByRole("button", { name: /enter the game/i }));

    expect(mockNavigate).toHaveBeenCalledWith("/game");
  });
});
