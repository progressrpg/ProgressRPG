import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import RegisterPage from "./RegisterPage";

const mockUseRegistrationStatus = vi.fn();
const mockRegister = vi.fn();

vi.mock("../../hooks/useRegistrationStatus", () => ({
  useRegistrationStatus: () => mockUseRegistrationStatus(),
}));

vi.mock("../../hooks/useRegister", () => ({
  default: () => ({ register: mockRegister, characterAvailable: true }),
}));

type TurnstileOptions = { sitekey: string; callback?: (token: string) => void };
const turnstileWidgets: { options: TurnstileOptions }[] = [];

function installTurnstile() {
  window.turnstile = {
    render: (_container: HTMLElement, options: TurnstileOptions) => {
      turnstileWidgets.push({ options });
      return `widget-${turnstileWidgets.length}`;
    },
    remove: vi.fn(),
    reset: vi.fn(),
  };
}

function openRegistration(turnstileSiteKey = "site-key-123") {
  mockUseRegistrationStatus.mockReturnValue({
    data: {
      registration_open: true,
      registration_enabled: true,
      self_serve_registration: true,
      turnstile_site_key: turnstileSiteKey,
    },
    isLoading: false,
  });
}

async function fillForm(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/^email/i), "new@example.com");
  await user.type(screen.getByLabelText(/^password/i), "sup3rs3cret!");
  await user.type(screen.getByLabelText(/confirm password/i), "sup3rs3cret!");
  await user.click(screen.getByRole("checkbox"));
}

function renderRegisterPage() {
  return render(
    <MemoryRouter>
      <RegisterPage />
    </MemoryRouter>
  );
}

describe("RegisterPage", () => {
  beforeEach(() => {
    turnstileWidgets.length = 0;
    mockRegister.mockReset();
    mockRegister.mockResolvedValue({ success: true, confirmationRequired: true });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    delete window.turnstile;
  });

  it("renders the kill-switch fallback when registration_enabled is false", () => {
    mockUseRegistrationStatus.mockReturnValue({
      data: {
        registration_open: true,
        registration_enabled: false,
        self_serve_registration: false,
      },
      isLoading: false,
    });

    renderRegisterPage();

    expect(
      screen.getByRole("heading", { name: "Registration is currently unavailable" })
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create Account" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Registration is temporarily full/i)).not.toBeInTheDocument();
  });

  it("renders the kill-switch fallback even for invited users", () => {
    mockUseRegistrationStatus.mockReturnValue({
      data: {
        registration_open: true,
        registration_enabled: false,
        self_serve_registration: false,
      },
      isLoading: false,
    });

    render(
      <MemoryRouter initialEntries={["/waitlist/redeem/some-invite-token"]}>
        <Routes>
          <Route path="/waitlist/redeem/:token" element={<RegisterPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(
      screen.getByRole("heading", { name: "Registration is currently unavailable" })
    ).toBeInTheDocument();
  });

  it("renders the registration form when registration is enabled, self-serve is on, and cap not reached", () => {
    mockUseRegistrationStatus.mockReturnValue({
      data: {
        registration_open: true,
        registration_enabled: true,
        self_serve_registration: true,
      },
      isLoading: false,
    });

    renderRegisterPage();

    expect(screen.getByRole("button", { name: "Create Account" })).toBeInTheDocument();
  });

  it("renders the waitlist form (not the register form) when self-serve registration is off", () => {
    mockUseRegistrationStatus.mockReturnValue({
      data: {
        registration_open: true,
        registration_enabled: true,
        self_serve_registration: false,
      },
      isLoading: false,
    });

    renderRegisterPage();

    expect(
      screen.getByRole("heading", { name: "Registration is by invite only" })
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create Account" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Join Waitlist" })).toBeInTheDocument();
  });

  it("still renders the registration form for an invited user even when self-serve registration is off", () => {
    mockUseRegistrationStatus.mockReturnValue({
      data: {
        registration_open: true,
        registration_enabled: true,
        self_serve_registration: false,
      },
      isLoading: false,
    });

    render(
      <MemoryRouter initialEntries={["/waitlist/redeem/some-invite-token"]}>
        <Routes>
          <Route path="/waitlist/redeem/:token" element={<RegisterPage />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByRole("button", { name: "Create Account" })).toBeInTheDocument();
  });

  it("makes the invite code optional when self-serve registration is on", () => {
    mockUseRegistrationStatus.mockReturnValue({
      data: {
        registration_open: true,
        registration_enabled: true,
        self_serve_registration: true,
      },
      isLoading: false,
    });

    renderRegisterPage();

    expect(screen.getByLabelText(/invite code \(optional\)/i)).not.toBeRequired();
  });

  it("renders the Turnstile widget when the form mounts after the script has loaded", () => {
    // Reproduces the SPA bug: the form only mounts once the registration-status
    // query resolves, long after Cloudflare's implicit DOM scan has run.
    installTurnstile();
    openRegistration();

    renderRegisterPage();

    expect(turnstileWidgets).toHaveLength(1);
    expect(turnstileWidgets[0].options.sitekey).toBe("site-key-123");
  });

  it("blocks submission until the security check produces a token", async () => {
    installTurnstile();
    openRegistration();
    const user = userEvent.setup();

    renderRegisterPage();
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /complete the security check/i
    );
    expect(mockRegister).not.toHaveBeenCalled();
  });

  it("submits with the token once the security check completes", async () => {
    installTurnstile();
    openRegistration();
    const user = userEvent.setup();

    renderRegisterPage();
    await fillForm(user);
    act(() => turnstileWidgets[0].options.callback?.("tok-abc"));

    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1));
    expect(mockRegister.mock.calls[0][5]).toBe("tok-abc");
  });

  it("does not gate submission on a token when no site key is configured", async () => {
    vi.stubEnv("VITE_TURNSTILE_SITE_KEY", "");
    openRegistration("");
    const user = userEvent.setup();

    renderRegisterPage();
    expect(screen.queryByTestId("turnstile")).not.toBeInTheDocument();

    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    await waitFor(() => expect(mockRegister).toHaveBeenCalledTimes(1));
  });

  it("falls back to the build-time site key when the API returns none", () => {
    vi.stubEnv("VITE_TURNSTILE_SITE_KEY", "env-key-456");
    installTurnstile();
    openRegistration("");

    renderRegisterPage();

    expect(turnstileWidgets).toHaveLength(1);
    expect(turnstileWidgets[0].options.sitekey).toBe("env-key-456");
  });

  it("requires the terms checkbox before submitting", async () => {
    installTurnstile();
    openRegistration();
    const user = userEvent.setup();

    renderRegisterPage();
    await user.type(screen.getByLabelText(/^email/i), "new@example.com");
    await user.type(screen.getByLabelText(/^password/i), "sup3rs3cret!");
    await user.type(screen.getByLabelText(/confirm password/i), "sup3rs3cret!");
    act(() => turnstileWidgets[0].options.callback?.("tok-abc"));

    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/agree to the Terms/i);
    expect(mockRegister).not.toHaveBeenCalled();
  });
});
