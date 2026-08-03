import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import NavDrawer from "./NavDrawer";

const mockUseAuth = vi.fn();
const mockUseFeatureFlag = vi.fn();

vi.mock("../../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../../hooks/useFeatureFlag", () => ({
  useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
}));

function renderDrawer(props: Partial<React.ComponentProps<typeof NavDrawer>> = {}) {
  const onClose = props.onClose ?? vi.fn();
  const utils = render(
    <MemoryRouter>
      <NavDrawer drawerOpen={props.drawerOpen ?? true} onClose={onClose} />
    </MemoryRouter>
  );
  return { onClose, ...utils };
}

// NOTE: the drawer is fixed-positioned and slid off-screen via `transform`,
// which happy-dom's CSS engine (used by this project's Vitest environment)
// misreports as `display: none` on the `<nav>`. That makes every role query
// inside it register as "inaccessible" even though it's genuinely visible in
// real browsers. Pass `hidden: true` to see past that environment quirk.
const HIDDEN = { hidden: true } as const;

describe("NavDrawer", () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false });
    mockUseFeatureFlag.mockReturnValue(false);
  });

  it("renders authenticated links when the user is logged in", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
    renderDrawer();

    expect(screen.getByRole("link", { name: /Timer/, ...HIDDEN })).toHaveAttribute(
      "href",
      "/timer"
    );
    expect(screen.getByRole("link", { name: /Your library/, ...HIDDEN })).toHaveAttribute(
      "href",
      "/library"
    );
    expect(screen.queryByRole("link", { name: /Log in/, ...HIDDEN })).not.toBeInTheDocument();
  });

  it("renders logged-out links when the user is not authenticated", () => {
    renderDrawer();

    expect(screen.getByRole("link", { name: /Home/, ...HIDDEN })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /Log in/, ...HIDDEN })).toHaveAttribute(
      "href",
      "/login"
    );
    expect(
      screen.getByRole("link", { name: "Join the waiting list", ...HIDDEN })
    ).toHaveAttribute("href", "/register");
    expect(screen.queryByRole("link", { name: /Timer/, ...HIDDEN })).not.toBeInTheDocument();
  });

  it("marks the drawer hidden and inert when closed", () => {
    const { container } = renderDrawer({ drawerOpen: false });

    // `inert` genuinely removes the element from the accessibility tree, so
    // `getByRole(..., { hidden: true })` can't see it either — query the DOM
    // directly instead.
    const nav = container.querySelector("nav")!;
    expect(nav).toHaveAttribute("aria-hidden", "true");
    expect(nav).toHaveAttribute("inert");
  });

  it("marks the drawer visible and not inert when open", () => {
    const { container } = renderDrawer({ drawerOpen: true });

    const nav = container.querySelector("nav")!;
    expect(nav).toHaveAttribute("aria-hidden", "false");
    expect(nav).not.toHaveAttribute("inert");
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDrawer({ drawerOpen: true });

    await user.click(screen.getByRole("button", { name: "Close navigation drawer", ...HIDDEN }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when the overlay is clicked", async () => {
    const user = userEvent.setup();
    const { onClose, container } = renderDrawer({ drawerOpen: true });

    const overlay = container.querySelector('[aria-hidden="true"].visible, [class*="overlay"]');
    expect(overlay).not.toBeNull();
    await user.click(overlay as Element);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when a nav link is clicked", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDrawer({ drawerOpen: true });

    await user.click(screen.getByRole("link", { name: /Home/, ...HIDDEN }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape is pressed while open", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDrawer({ drawerOpen: true });

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not call onClose on Escape when the drawer is closed", async () => {
    const user = userEvent.setup();
    const { onClose } = renderDrawer({ drawerOpen: false });

    await user.keyboard("{Escape}");

    expect(onClose).not.toHaveBeenCalled();
  });

  it("focuses the drawer nav when opened", () => {
    const { container } = renderDrawer({ drawerOpen: true });

    const nav = container.querySelector("nav")!;
    expect(nav).toHaveFocus();
  });
});
