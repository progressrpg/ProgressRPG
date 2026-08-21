import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OnlineCountProvider, useOnlineCount } from "./OnlineCountContext";
import { useGame } from "../hooks/useGame";

vi.mock("../hooks/useGame", () => ({ useGame: vi.fn() }));

const mockedUseGame = useGame as ReturnType<typeof vi.fn>;

function Consumer() {
  const { onlinePlayerCount, setOnlinePlayerCount } = useOnlineCount();
  return (
    <div>
      <span data-testid="count">{onlinePlayerCount}</span>
      <button onClick={() => setOnlinePlayerCount(42)}>set</button>
    </div>
  );
}

describe("OnlineCountProvider", () => {
  it("initializes from useGame's initialOnlineCount", () => {
    mockedUseGame.mockReturnValue({ initialOnlineCount: 9 });

    render(
      <OnlineCountProvider>
        <Consumer />
      </OnlineCountProvider>
    );

    expect(screen.getByTestId("count")).toHaveTextContent("9");
  });

  it("updates the count via setOnlinePlayerCount", () => {
    mockedUseGame.mockReturnValue({ initialOnlineCount: 0 });

    render(
      <OnlineCountProvider>
        <Consumer />
      </OnlineCountProvider>
    );

    act(() => {
      screen.getByText("set").click();
    });

    expect(screen.getByTestId("count")).toHaveTextContent("42");
  });
});

describe("useOnlineCount", () => {
  it("throws when used outside an OnlineCountProvider", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    function BareConsumer() {
      useOnlineCount();
      return null;
    }

    expect(() => render(<BareConsumer />)).toThrow(
      "useOnlineCount must be used within an OnlineCountProvider"
    );

    consoleErrorSpy.mockRestore();
  });
});
