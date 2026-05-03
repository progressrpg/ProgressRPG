import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import LoginPage from "./LoginPage";

const mockLoginWithJwt = vi.fn();
const mockAuthLogin = vi.fn();
const mockNavigate = vi.fn();

vi.mock("../../hooks/useLogin", () => ({
  default: () => mockLoginWithJwt,
}));

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    login: mockAuthLogin,
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    mockLoginWithJwt.mockReset();
    mockAuthLogin.mockReset();
    mockNavigate.mockReset();
  });

  it("submits credentials and navigates to the game after a successful login", async () => {
    const user = userEvent.setup();
    mockLoginWithJwt.mockResolvedValue({
      success: true,
      tokens: {
        access_token: "access-123",
        refresh_token: "refresh-123",
      },
    });
    mockAuthLogin.mockResolvedValue({ onboarding_step: 4 });

    renderLoginPage();

    await user.type(screen.getByPlaceholderText("Email"), "player@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "secretpass");
    await user.click(screen.getByRole("button", { name: "Log In" }));

    await waitFor(() => {
      expect(mockLoginWithJwt).toHaveBeenCalledWith("player@example.com", "secretpass");
    });
    expect(mockAuthLogin).toHaveBeenCalledWith("access-123", "refresh-123");
    expect(mockNavigate).toHaveBeenCalledWith("/game");
  });

  it("navigates to onboarding when the authenticated user is still onboarding", async () => {
    const user = userEvent.setup();
    mockLoginWithJwt.mockResolvedValue({
      success: true,
      tokens: {
        access_token: "access-123",
        refresh_token: "refresh-123",
      },
    });
    mockAuthLogin.mockResolvedValue({ onboarding_step: 2 });

    renderLoginPage();

    await user.type(screen.getByPlaceholderText("Email"), "player@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "secretpass");
    await user.click(screen.getByRole("button", { name: "Log In" }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/onboarding");
    });
  });

  it("shows a login error when JWT login fails", async () => {
    const user = userEvent.setup();
    mockLoginWithJwt.mockResolvedValue({
      success: false,
      error: "Invalid email or password; please try again.",
    });

    renderLoginPage();

    await user.type(screen.getByPlaceholderText("Email"), "player@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "wrongpass");
    await user.click(screen.getByRole("button", { name: "Log In" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password; please try again."
    );
    expect(mockAuthLogin).not.toHaveBeenCalled();
  });
});
