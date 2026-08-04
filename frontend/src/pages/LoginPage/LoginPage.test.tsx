import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { MemoryRouter } from "react-router";
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

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
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

  it("submits credentials without remember me by default", async () => {
    const user = userEvent.setup();
    mockLoginWithJwt.mockResolvedValue({
      success: true,
      tokens: {
        access_token: "access-123",
        refresh_token: "refresh-123",
      },
    });
    mockAuthLogin.mockResolvedValue({});

    renderLoginPage();

    await user.type(screen.getByPlaceholderText("Email"), "player@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "secretpass");
    await user.click(screen.getByRole("button", { name: "Log In" }));

    await waitFor(() => {
      expect(mockLoginWithJwt).toHaveBeenCalledWith("player@example.com", "secretpass", false);
    });
    expect(mockAuthLogin).toHaveBeenCalledWith("access-123", "refresh-123", { rememberMe: false });
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });

  it("submits remembered sessions when the checkbox is selected", async () => {
    const user = userEvent.setup();
    mockLoginWithJwt.mockResolvedValue({
      success: true,
      tokens: {
        access_token: "access-123",
        refresh_token: "refresh-123",
      },
    });
    mockAuthLogin.mockResolvedValue({});

    renderLoginPage();

    await user.type(screen.getByPlaceholderText("Email"), "player@example.com");
    await user.type(screen.getByPlaceholderText("Password"), "secretpass");
    await user.click(screen.getByRole("checkbox", { name: "Remember me" }));
    await user.click(screen.getByRole("button", { name: "Log In" }));

    await waitFor(() => {
      expect(mockLoginWithJwt).toHaveBeenCalledWith("player@example.com", "secretpass", true);
    });
    expect(mockAuthLogin).toHaveBeenCalledWith("access-123", "refresh-123", { rememberMe: true });
    expect(mockNavigate).toHaveBeenCalledWith("/");
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
