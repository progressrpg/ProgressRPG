import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TamaguiProvider } from "tamagui";
import MapDetailCard from "./MapDetailCard";
import tamaguiConfig from "../../../tamagui.config";

// MapDetailCard's underlying DetailSurface needs a TamaguiProvider ancestor -
// the app root (src/main.tsx) provides this in production; tests need their own.
function renderCard(overrides: Partial<React.ComponentProps<typeof MapDetailCard>> = {}) {
  const props = {
    open: true,
    title: "Riverside",
    onClose: vi.fn(),
    children: <p>Card content</p>,
    ...overrides,
  };
  render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      <MapDetailCard {...props} />
    </TamaguiProvider>
  );
  return props;
}

describe("MapDetailCard", () => {
  it("renders the title and content when open", () => {
    renderCard();
    expect(screen.getByRole("dialog", { name: "Riverside" })).toBeInTheDocument();
    expect(screen.getAllByText("Riverside").length).toBeGreaterThan(0);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    renderCard({ open: false });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = userEvent.setup();
    const { onClose } = renderCard();
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not render a fly-to button when onFlyTo is omitted", () => {
    renderCard();
    expect(screen.queryByRole("button", { name: "Fly to" })).not.toBeInTheDocument();
  });

  it("calls onFlyTo when the fly-to button is clicked", async () => {
    const user = userEvent.setup();
    const onFlyTo = vi.fn();
    renderCard({ onFlyTo });
    await user.click(screen.getByRole("button", { name: "Fly to" }));
    expect(onFlyTo).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape is pressed", async () => {
    const user = userEvent.setup();
    const { onClose } = renderCard();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders into the provided container instead of document.body", () => {
    const container = document.createElement("div");
    container.setAttribute("data-testid", "map-wrapper");
    document.body.appendChild(container);

    renderCard({ container });

    expect(container.querySelector('[role="dialog"]')).not.toBeNull();

    document.body.removeChild(container);
  });
});
