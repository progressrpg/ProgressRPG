import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render as rtlRender, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TamaguiProvider } from "tamagui";

import Account from "./Account";
import tamaguiConfig from "../../../tamagui.config";

const mockUseGame = vi.fn();
const mockUpdatePlayer = vi.fn();
const mockDownloadUserData = vi.fn();
const mockDeleteAccount = vi.fn();
const mockFetchPreferences = vi.fn();
const mockUpdatePreferences = vi.fn();
const mockFetchTimezoneChoices = vi.fn();
const mockUpdateUserSettings = vi.fn();
const mockSetUser = vi.fn();
const mockUseAuth = vi.fn();

const TEST_BILLING_PORTAL_URL = "https://billing.stripe.com/p/login/test_portal";

vi.mock("../../hooks/useGame", () => ({
  useGame: () => mockUseGame(),
}));

vi.mock("../../api/player", () => ({
  updatePlayer: (...args) => mockUpdatePlayer(...args),
  downloadUserData: (...args) => mockDownloadUserData(...args),
  deleteAccount: (...args) => mockDeleteAccount(...args),
}));

vi.mock("../../api/preferences", () => ({
  fetchPreferences: (...args) => mockFetchPreferences(...args),
  updatePreferences: (...args) => mockUpdatePreferences(...args),
}));

vi.mock("../../api/user", () => ({
  fetchTimezoneChoices: (...args) => mockFetchTimezoneChoices(...args),
  updateUserSettings: (...args) => mockUpdateUserSettings(...args),
}));

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../../hooks/useAppConfig", () => ({
  useAppConfig: () => ({ data: { stripe_billing_portal_url: TEST_BILLING_PORTAL_URL } }),
}));

// Account renders Tabs (mirroring LibraryPage, see #584), which needs a
// TamaguiProvider ancestor - unlike Radix's Tabs.Root, it isn't usable
// standalone. The app root (src/main.tsx) provides this in production;
// tests need their own.
function render(...args: Parameters<typeof rtlRender>) {
  const [ui, options] = args;
  return rtlRender(ui, {
    wrapper: ({ children }) => (
      <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
        {children}
      </TamaguiProvider>
    ),
    ...options,
  });
}

const tierOneAchievements = [
  {
    type: "level",
    label: "Player level",
    symbol: "⭐",
    tier: 1,
    complete: false,
    color: "grey",
    value: 0,
    threshold: 2,
    next_threshold: 5,
  },
  {
    type: "time",
    label: "Total time",
    symbol: "⏱️",
    tier: 1,
    complete: false,
    color: "grey",
    value: 0,
    threshold: 1800,
    next_threshold: 18000,
  },
  {
    type: "activities",
    label: "Activities",
    symbol: "✅",
    tier: 1,
    complete: false,
    color: "grey",
    value: 0,
    threshold: 5,
    next_threshold: 25,
  },
];

const tierTwoAchievements = [
  {
    type: "level",
    label: "Player level",
    symbol: "⭐",
    tier: 2,
    complete: false,
    color: "green",
    value: 2,
    threshold: 5,
    next_threshold: 10,
  },
  {
    type: "time",
    label: "Total time",
    symbol: "⏱️",
    tier: 2,
    complete: false,
    color: "green",
    value: 1800,
    threshold: 18000,
    next_threshold: 72000,
  },
  {
    type: "activities",
    label: "Activities",
    symbol: "✅",
    tier: 2,
    complete: false,
    color: "green",
    value: 5,
    threshold: 25,
    next_threshold: 100,
  },
];

const completedAchievements = [
  {
    type: "level",
    label: "Player level",
    symbol: "⭐",
    tier: 5,
    complete: true,
    color: "gold",
    value: 50,
    threshold: 50,
    next_threshold: null,
  },
  {
    type: "time",
    label: "Total time",
    symbol: "⏱️",
    tier: 5,
    complete: true,
    color: "gold",
    value: 1080000,
    threshold: 1080000,
    next_threshold: null,
  },
  {
    type: "activities",
    label: "Activities",
    symbol: "✅",
    tier: 5,
    complete: true,
    color: "gold",
    value: 2000,
    threshold: 2000,
    next_threshold: null,
  },
];

function mockPlayer(overrides = {}) {
  return {
    name: "player_01234",
    level: 3,
    xp: 25,
    xp_next_level: 100,
    total_activities: 4,
    total_time: 5400,
    achievements: tierTwoAchievements,
    is_premium: false,
    ...overrides,
  };
}

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
    mockFetchPreferences.mockReset().mockResolvedValue({ preferences: [] });
    mockUpdatePreferences.mockReset();
    mockFetchTimezoneChoices.mockReset().mockResolvedValue({
      timezones: [
        { value: "UTC", label: "UTC" },
        { value: "Europe/London", label: "Europe/London" },
        { value: "America/New_York", label: "America/New York" },
      ],
    });
    mockUpdateUserSettings.mockReset();
    mockSetUser.mockReset();
    mockUseAuth.mockReset().mockReturnValue({
      user: {
        email: "test@example.com",
        is_confirmed: true,
        is_staff: false,
        is_superuser: false,
        date_of_birth: null,
        timezone: "UTC",
      },
      setUser: mockSetUser,
    });
    mockUseGame.mockReturnValue({
      player: mockPlayer(),
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

  it("shows upgrade button in billing for free users", () => {
    renderAccount();

    expect(
      screen.getByText("Ready for more focus tools and rewards?")
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Upgrade" })).toHaveAttribute(
      "href",
      "/upgrade"
    );
    expect(
      screen.queryByText(/Manage your subscription and billing details/i)
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Open Billing Portal" })
    ).not.toBeInTheDocument();
  });

  it("renders three next-goal achievement badges", () => {
    renderAccount();

    expect(screen.getByRole("heading", { name: "Achievements" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Player level" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Total time" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Activities" })).toBeInTheDocument();
    expect(screen.getAllByText("Tier 2")).toHaveLength(3);
    expect(screen.getByText("2 / 5")).toBeInTheDocument();
    expect(screen.getByText("30m / 5h")).toBeInTheDocument();
    expect(screen.getByText("5 / 25")).toBeInTheDocument();
  });

  it("shows tier one goals for below-threshold stats", () => {
    mockUseGame.mockReturnValue({
      player: mockPlayer({
        level: 0,
        total_activities: 0,
        total_time: 0,
        achievements: tierOneAchievements,
      }),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    expect(screen.getAllByText("Tier 1")).toHaveLength(3);
    expect(screen.getByText("0 / 2")).toBeInTheDocument();
    expect(screen.getByText("0m / 30m")).toBeInTheDocument();
    expect(screen.getByText("0 / 5")).toBeInTheDocument();
  });

  it("shows completed max-tier achievements", () => {
    mockUseGame.mockReturnValue({
      player: mockPlayer({
        level: 50,
        total_activities: 2000,
        total_time: 1080000,
        achievements: completedAchievements,
      }),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    expect(screen.getAllByText("Tier 5")).toHaveLength(3);
    expect(screen.getAllByText("Complete")).toHaveLength(3);
    expect(screen.getAllByText("Max tier")).toHaveLength(3);
  });

  it("shows billing portal controls for premium users", () => {
    mockUseGame.mockReturnValue({
      player: mockPlayer({ is_premium: true }),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    expect(
      screen.getByText(/Manage your subscription and billing details/i)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open billing portal" })
    ).toHaveAttribute("href", TEST_BILLING_PORTAL_URL);
    expect(screen.queryByRole("link", { name: "Upgrade" })).not.toBeInTheDocument();
  });

  it("shows the trial status line with days remaining for trialing users", () => {
    const trialEnd = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString();
    mockUseGame.mockReturnValue({
      player: mockPlayer({
        is_premium: true,
        is_trialing: true,
        trial_end: trialEnd,
      }),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    expect(screen.getByText(/Free trial.*5 days remaining/)).toBeInTheDocument();
  });

  it("shows singular 'day' when exactly one day remains", () => {
    const trialEnd = new Date(Date.now() + 12 * 60 * 60 * 1000).toISOString();
    mockUseGame.mockReturnValue({
      player: mockPlayer({
        is_premium: true,
        is_trialing: true,
        trial_end: trialEnd,
      }),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    expect(screen.getByText(/Free trial.*1 day remaining/)).toBeInTheDocument();
  });

  it("does not show the trial status line for non-trialing free users", () => {
    mockUseGame.mockReturnValue({
      player: mockPlayer({ is_premium: false, is_trialing: false, trial_end: null }),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    expect(screen.queryByText(/Free trial/)).not.toBeInTheDocument();
  });

  it("does not show the trial status line once a premium user's trial has ended", () => {
    mockUseGame.mockReturnValue({
      player: mockPlayer({ is_premium: true, is_trialing: false, trial_end: null }),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    expect(screen.queryByText(/Free trial/)).not.toBeInTheDocument();
  });

  it("saves a valid name and refetches player data on success", async () => {
    const user = userEvent.setup();
    const fetchPlayerAndCharacter = vi.fn().mockResolvedValue(undefined);
    mockUseGame.mockReturnValue({
      player: mockPlayer(),
      loading: false,
      fetchPlayerAndCharacter,
    });
    mockUpdatePlayer.mockResolvedValue({ name: "New Name" });

    renderAccount();

    await user.click(screen.getByRole("button", { name: /edit name/i }));
    const input = screen.getByRole("textbox");
    await user.clear(input);
    await user.type(input, "New Name");
    await user.click(screen.getByRole("button", { name: /save name/i }));

    expect(mockUpdatePlayer).toHaveBeenCalledWith({ name: "New Name" }, expect.anything());
    await vi.waitFor(() => expect(screen.queryByRole("textbox")).not.toBeInTheDocument());
    expect(fetchPlayerAndCharacter).toHaveBeenCalled();
  });

  it("shows an error and stays in edit mode when saving the name fails", async () => {
    const user = userEvent.setup();
    mockUseGame.mockReturnValue({
      player: mockPlayer(),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });
    mockUpdatePlayer.mockRejectedValue(new Error("Name already taken"));

    renderAccount();

    await user.click(screen.getByRole("button", { name: /edit name/i }));
    const input = screen.getByRole("textbox");
    await user.clear(input);
    await user.type(input, "New Name");
    await user.click(screen.getByRole("button", { name: /save name/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Name already taken");
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("cancels editing and discards the draft name", async () => {
    const user = userEvent.setup();
    mockUseGame.mockReturnValue({
      player: mockPlayer(),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    await user.click(screen.getByRole("button", { name: /edit name/i }));
    await user.clear(screen.getByRole("textbox"));
    await user.type(screen.getByRole("textbox"), "Discarded");
    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(mockUpdatePlayer).not.toHaveBeenCalled();
    expect(screen.getByText("player_01234")).toBeInTheDocument();
  });

  it("downloads user data when the download button is clicked", async () => {
    const user = userEvent.setup();
    mockUseGame.mockReturnValue({
      player: mockPlayer(),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });
    mockDownloadUserData.mockResolvedValue({ url: "http://example.com/data.zip" });

    renderAccount();

    await user.click(screen.getByRole("button", { name: /download my data/i }));

    expect(mockDownloadUserData).toHaveBeenCalled();
    expect(await screen.findByRole("button", { name: /download my data/i })).toBeInTheDocument();
  });

  it("requires typing DELETE before the delete-account button is enabled", async () => {
    const user = userEvent.setup();
    mockUseGame.mockReturnValue({
      player: mockPlayer(),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    await user.click(screen.getByRole("button", { name: /delete my account/i }));
    const confirmButton = screen.getByRole("button", { name: /confirm delete/i });
    expect(confirmButton).toBeDisabled();

    await user.type(screen.getByPlaceholderText("Type DELETE to confirm"), "wrong");
    expect(confirmButton).toBeDisabled();

    await user.clear(screen.getByPlaceholderText("Type DELETE to confirm"));
    await user.type(screen.getByPlaceholderText("Type DELETE to confirm"), "DELETE");
    expect(confirmButton).not.toBeDisabled();
  });

  it("deletes the account, clears storage, and navigates home on confirm", async () => {
    const user = userEvent.setup();
    mockUseGame.mockReturnValue({
      player: mockPlayer(),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });
    mockDeleteAccount.mockResolvedValue(undefined);
    localStorage.setItem("leftover", "1");

    renderAccount();

    await user.click(screen.getByRole("button", { name: /delete my account/i }));
    await user.type(screen.getByPlaceholderText("Type DELETE to confirm"), "DELETE");
    await user.click(screen.getByRole("button", { name: /confirm delete/i }));

    await vi.waitFor(() => expect(mockDeleteAccount).toHaveBeenCalled());
    await vi.waitFor(() => expect(localStorage.getItem("leftover")).toBeNull());
  });

  it("cancels the delete-account confirmation and resets the typed text", async () => {
    const user = userEvent.setup();
    mockUseGame.mockReturnValue({
      player: mockPlayer(),
      loading: false,
      fetchPlayerAndCharacter: vi.fn(),
    });

    renderAccount();

    await user.click(screen.getByRole("button", { name: /delete my account/i }));
    await user.type(screen.getByPlaceholderText("Type DELETE to confirm"), "DEL");
    await user.click(screen.getByRole("button", { name: /^cancel$/i }));

    expect(screen.queryByPlaceholderText("Type DELETE to confirm")).not.toBeInTheDocument();
    expect(mockDeleteAccount).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /delete my account/i }));
    expect(screen.getByPlaceholderText("Type DELETE to confirm")).toHaveValue("");
  });

  it("defaults to the Account tab, hiding preferences content", () => {
    renderAccount();

    expect(screen.getByRole("heading", { name: "Player" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Notifications" })).not.toBeInTheDocument();
  });

  it("switches to the Preferences tab and lists preferences", async () => {
    const user = userEvent.setup();
    mockFetchPreferences.mockResolvedValue({
      preferences: [
        {
          key: "notifications__inactivity_reminder_emails",
          section: "notifications",
          name: "inactivity_reminder_emails",
          verbose_name: "Inactivity reminder emails",
          help_text: "Send a reminder email after 7 days of inactivity.",
          type: "boolean",
          value: true,
        },
      ],
    });

    renderAccount();

    await user.click(screen.getByRole("tab", { name: "Preferences" }));

    expect(await screen.findByRole("heading", { name: "Notifications" })).toBeInTheDocument();
    const checkbox = await screen.findByRole("switch", { name: /inactivity reminder emails/i });
    expect(checkbox).toBeChecked();
    expect(screen.queryByRole("heading", { name: "Player" })).not.toBeInTheDocument();
  });

  it("toggles a preference off and sends the patch", async () => {
    const user = userEvent.setup();
    mockFetchPreferences.mockResolvedValue({
      preferences: [
        {
          key: "notifications__inactivity_reminder_emails",
          section: "notifications",
          name: "inactivity_reminder_emails",
          verbose_name: "Inactivity reminder emails",
          help_text: "Send a reminder email after 7 days of inactivity.",
          type: "boolean",
          value: true,
        },
      ],
    });
    mockUpdatePreferences.mockResolvedValue({
      preferences: [
        {
          key: "notifications__inactivity_reminder_emails",
          section: "notifications",
          name: "inactivity_reminder_emails",
          verbose_name: "Inactivity reminder emails",
          help_text: "Send a reminder email after 7 days of inactivity.",
          type: "boolean",
          value: false,
        },
      ],
    });

    renderAccount();

    await user.click(screen.getByRole("tab", { name: "Preferences" }));
    const checkbox = await screen.findByRole("switch", { name: /inactivity reminder emails/i });
    await user.click(checkbox);

    expect(mockUpdatePreferences).toHaveBeenCalledWith(
      { notifications__inactivity_reminder_emails: false },
      expect.anything()
    );
    await vi.waitFor(() => expect(checkbox).not.toBeChecked());
  });

  it("shows the saved timezone on the Preferences tab", async () => {
    const user = userEvent.setup();

    renderAccount();

    await user.click(screen.getByRole("tab", { name: "Preferences" }));

    expect(await screen.findByRole("heading", { name: "Timezone" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Timezone" })).toHaveValue("UTC");
  });

  it("updates the timezone when a new option is selected from the list", async () => {
    const user = userEvent.setup();
    mockUpdateUserSettings.mockResolvedValue({
      email: "test@example.com",
      is_confirmed: true,
      is_staff: false,
      is_superuser: false,
      date_of_birth: null,
      timezone: "Europe/London",
    });

    renderAccount();

    await user.click(screen.getByRole("tab", { name: "Preferences" }));
    const combobox = await screen.findByRole("combobox", { name: "Timezone" });
    await user.click(combobox);
    await user.click(await screen.findByRole("option", { name: "Europe/London" }));

    expect(mockUpdateUserSettings).toHaveBeenCalledWith(
      { timezone: "Europe/London" },
      expect.anything()
    );
    await vi.waitFor(() => expect(mockSetUser).toHaveBeenCalled());
  });

  it("offers to switch to the browser-detected timezone when it differs from the saved one", async () => {
    const user = userEvent.setup();
    vi.spyOn(Intl, "DateTimeFormat").mockImplementation(
      () =>
        ({
          resolvedOptions: () => ({ timeZone: "Europe/London" }),
        }) as Intl.DateTimeFormat
    );
    mockUpdateUserSettings.mockResolvedValue({
      email: "test@example.com",
      is_confirmed: true,
      is_staff: false,
      is_superuser: false,
      date_of_birth: null,
      timezone: "Europe/London",
    });

    renderAccount();

    await user.click(screen.getByRole("tab", { name: "Preferences" }));
    const hintButton = await screen.findByRole("button", {
      name: /use detected timezone \(europe\/london\)/i,
    });

    await user.click(hintButton);

    expect(mockUpdateUserSettings).toHaveBeenCalledWith(
      { timezone: "Europe/London" },
      expect.anything()
    );

    vi.restoreAllMocks();
  });
});
