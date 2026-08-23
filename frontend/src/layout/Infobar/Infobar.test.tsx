import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

import Infobar from "./Infobar";

const mockUseGame = vi.fn();

vi.mock("../../hooks/useGame", () => ({
  useGame: () => mockUseGame(),
}));

const basePlayer = {
  name: "Alex",
  xp: 10,
  xp_next_level: 100,
  level: 1,
  is_premium: false,
  achievements: [],
  progressive_unlocks: { infobar: true, library: true, map: true },
};

describe("Infobar", () => {
  beforeEach(() => {
    mockUseGame.mockReturnValue({ player: basePlayer, loading: false });
  });

  it("renders player info when progressive_unlocks.infobar is true", () => {
    render(<Infobar />);

    expect(screen.getByText("Alex")).toBeInTheDocument();
  });

  it("renders nothing when progressive_unlocks.infobar is false", () => {
    mockUseGame.mockReturnValue({
      player: {
        ...basePlayer,
        progressive_unlocks: { infobar: false, library: false, map: false },
      },
      loading: false,
    });

    const { container } = render(<Infobar />);

    expect(container).toBeEmptyDOMElement();
  });
});
