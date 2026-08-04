import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import Navbar from "./Navbar";

const mockUseAuth = vi.fn();
const mockUseGame = vi.fn();
const mockUseFeatureFlag = vi.fn();
const mockUseAnnouncements = vi.fn();
const markOneMutate = vi.fn();
const markAllMutate = vi.fn();

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../../hooks/useGame", () => ({
  useGame: () => mockUseGame(),
}));

vi.mock("../../hooks/useFeatureFlag", () => ({
  useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
}));

vi.mock("../../hooks/useAnnouncements", () => ({
  useAnnouncements: (...args: unknown[]) => mockUseAnnouncements(...args),
  useMarkAllAnnouncementsRead: () => ({
    mutateAsync: markAllMutate,
    isPending: false,
  }),
  useMarkAnnouncementRead: () => ({
    mutateAsync: markOneMutate,
    isPending: false,
  }),
}));

function renderNavbar(
  props: Partial<React.ComponentProps<typeof Navbar>> = {},
  initialPath = "/"
) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Navbar {...props} />
    </MemoryRouter>
  );
}

describe("Navbar", () => {
  beforeEach(() => {
    markOneMutate.mockReset();
    markAllMutate.mockReset();
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
    mockUseGame.mockReturnValue({
      announcementUnreadCount: 0,
      setAnnouncementUnreadCount: vi.fn(),
    });
    mockUseFeatureFlag.mockReturnValue(false);
    mockUseAnnouncements.mockReturnValue({ data: undefined, isLoading: false });
  });

  it("renders logged-out state with a Home link and Log in buttons", () => {
    renderNavbar();

    expect(screen.getByRole("link", { name: "Go to home" })).toHaveAttribute("href", "/");
    expect(screen.getAllByRole("link", { name: /Log in/ }).length).toBeGreaterThan(0);
    expect(screen.queryByLabelText("Go to your account")).not.toBeInTheDocument();
  });

  it("renders authenticated state with timer, library, account and logout links", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    renderNavbar();

    expect(screen.getByRole("link", { name: "Go to timer" })).toHaveAttribute("href", "/timer");
    expect(screen.getByRole("link", { name: "Go to your library" })).toHaveAttribute(
      "href",
      "/library"
    );
    expect(screen.getByRole("link", { name: "Go to your account" })).toHaveAttribute(
      "href",
      "/account"
    );
    expect(screen.getByRole("link", { name: "Log out of your account" })).toHaveAttribute(
      "href",
      "/logout"
    );
  });

  it("renders the help button when onHelpClick is provided and calls it on click", async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    const onHelpClick = vi.fn();
    renderNavbar({ onHelpClick });

    const helpButton = screen.getByRole("button", { name: "Open tutorial" });
    await user.click(helpButton);

    expect(onHelpClick).toHaveBeenCalledTimes(1);
  });

  it("does not render the help button when onHelpClick is not provided", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    renderNavbar();

    expect(screen.queryByRole("button", { name: "Open tutorial" })).not.toBeInTheDocument();
  });

  it("calls onMenuClick when the mobile menu button is clicked", async () => {
    const user = userEvent.setup();
    const onMenuClick = vi.fn();
    renderNavbar({ onMenuClick });

    // The mobile icons bar is hidden at the desktop breakpoint via a media
    // query that happy-dom's CSS engine (this project's Vitest environment)
    // resolves as `display: none` regardless of viewport, which makes the
    // button register as inaccessible even though it renders fine in browsers.
    await user.click(screen.getByRole("button", { name: "Open menu", hidden: true }));

    expect(onMenuClick).toHaveBeenCalledTimes(1);
  });

  it("does not render the announcements bell when the feature flag is disabled", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    mockUseFeatureFlag.mockReturnValue(false);
    renderNavbar();

    expect(screen.queryByRole("button", { name: "Announcements" })).not.toBeInTheDocument();
  });

  it("renders the announcements bell with an unread badge when enabled", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    mockUseFeatureFlag.mockReturnValue(true);
    mockUseAnnouncements.mockReturnValue({
      data: { results: [], unread_count: 3 },
      isLoading: false,
    });
    renderNavbar();

    const trigger = screen.getByRole("button", { name: "Announcements" });
    expect(within(trigger).getByText("3")).toBeInTheDocument();
  });

  it("shows announcements in the popover and marks all read", async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    mockUseFeatureFlag.mockReturnValue(true);
    mockUseAnnouncements.mockReturnValue({
      data: {
        results: [
          {
            id: 1,
            title: "New feature",
            summary: "Summary text",
            body: "Body text",
            is_read: false,
          },
        ],
        unread_count: 1,
      },
      isLoading: false,
    });
    markAllMutate.mockResolvedValue({ unread_count: 0 });
    renderNavbar();

    await user.click(screen.getByRole("button", { name: "Announcements" }));

    expect(screen.getByText("New feature")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Mark all read" }));

    expect(markAllMutate).toHaveBeenCalledTimes(1);
  });

  it("marks a single announcement as read", async () => {
    const user = userEvent.setup();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    mockUseFeatureFlag.mockReturnValue(true);
    mockUseAnnouncements.mockReturnValue({
      data: {
        results: [
          {
            id: 42,
            title: "New feature",
            summary: "",
            body: "Body text",
            is_read: false,
          },
        ],
        unread_count: 1,
      },
      isLoading: false,
    });
    markOneMutate.mockResolvedValue({ unread_count: 0 });
    renderNavbar();

    await user.click(screen.getByRole("button", { name: "Announcements" }));
    await user.click(screen.getByRole("button", { name: "Mark read" }));

    expect(markOneMutate).toHaveBeenCalledWith(42);
  });

  it("highlights the timer button as primary on the timer page", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    renderNavbar({}, "/timer");

    const timerLink = screen.getByRole("link", { name: "Go to timer" });
    const button = within(timerLink).getByRole("button");
    expect(button.className).toMatch(/primary/);
  });

  it("highlights the account button as primary on the account page", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    renderNavbar({}, "/account");

    const accountLink = screen.getByRole("link", { name: "Go to your account" });
    const button = within(accountLink).getByRole("button");
    expect(button.className).toMatch(/primary/);
  });
});
