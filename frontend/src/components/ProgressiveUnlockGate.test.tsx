import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

import ProgressiveUnlockGate from "./ProgressiveUnlockGate";

const mockUseGame = vi.fn();

vi.mock("../hooks/useGame", () => ({
  useGame: () => mockUseGame(),
}));

describe("ProgressiveUnlockGate", () => {
  beforeEach(() => {
    mockUseGame.mockReset();
  });

  it("renders children when the unlock is true", () => {
    mockUseGame.mockReturnValue({
      player: { progressive_unlocks: { library: true } },
    });

    render(
      <ProgressiveUnlockGate unlock="library" title="Locked" message="msg">
        <p>Library content</p>
      </ProgressiveUnlockGate>
    );

    expect(screen.getByText("Library content")).toBeInTheDocument();
  });

  it("renders the locked fallback when the unlock is false", () => {
    mockUseGame.mockReturnValue({
      player: { progressive_unlocks: { library: false } },
    });

    render(
      <ProgressiveUnlockGate unlock="library" title="Locked" message="Do more stuff">
        <p>Library content</p>
      </ProgressiveUnlockGate>
    );

    expect(screen.queryByText("Library content")).not.toBeInTheDocument();
    expect(screen.getByText("Locked")).toBeInTheDocument();
    expect(screen.getByText("Do more stuff")).toBeInTheDocument();
  });

  it("renders the locked fallback when there is no player yet", () => {
    mockUseGame.mockReturnValue({ player: null });

    render(
      <ProgressiveUnlockGate unlock="library" title="Locked" message="msg">
        <p>Library content</p>
      </ProgressiveUnlockGate>
    );

    expect(screen.getByText("Locked")).toBeInTheDocument();
  });
});
