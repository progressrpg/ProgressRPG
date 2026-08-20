import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import BackToTopButton from "./BackToTopButton";

describe("BackToTopButton", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("scrolls smoothly to the top when clicked, by default", async () => {
    const user = userEvent.setup();
    const scrollTo = vi.fn();
    vi.stubGlobal("scrollTo", scrollTo);
    vi.spyOn(window, "matchMedia").mockReturnValue({
      matches: false,
    } as MediaQueryList);

    render(<BackToTopButton />);
    await user.click(screen.getByRole("button", { name: "Back to top" }));

    expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "smooth" });
  });

  it("scrolls instantly when the user prefers reduced motion", async () => {
    const user = userEvent.setup();
    const scrollTo = vi.fn();
    vi.stubGlobal("scrollTo", scrollTo);
    vi.spyOn(window, "matchMedia").mockReturnValue({
      matches: true,
    } as MediaQueryList);

    render(<BackToTopButton />);
    await user.click(screen.getByRole("button", { name: "Back to top" }));

    expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "auto" });
  });
});
