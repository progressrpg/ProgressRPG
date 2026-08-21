import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TamaguiProvider } from "tamagui";

import { TooltipProvider } from "../Tooltip/Tooltip";
import LogOfflineActivityModal from "./LogOfflineActivityModal";
import tamaguiConfig from "../../../tamagui.config";

const logMutate = vi.fn();
const fetchPlayerAndCharacter = vi.fn();
let gameValue: Record<string, unknown>;

vi.mock("../../hooks/useActivities", () => ({
  useLogOfflineActivity: () => ({ mutate: logMutate, isPending: false }),
}));

vi.mock("../../hooks/useGame", () => ({
  useGame: () => gameValue,
}));

// Stub the autocomplete input so these tests don't depend on the search cache.
vi.mock("../EntitySearchInput/EntitySearchInput", () => ({
  default: ({
    value,
    onChange,
    placeholder,
  }: {
    value: string;
    onChange?: (v: string) => void;
    placeholder?: string;
  }) => (
    <input
      aria-label="Task"
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange?.(event.target.value)}
    />
  ),
}));

// LogOfflineActivityModal renders Modal (#582), which needs a
// TamaguiProvider ancestor - unlike Radix's Dialog.Root, it isn't usable
// standalone. The app root (src/main.tsx) provides this in production;
// tests need their own.
function renderModal(onClose = vi.fn()) {
  return render(
    <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
      <TooltipProvider>
        <LogOfflineActivityModal onClose={onClose} />
      </TooltipProvider>
    </TamaguiProvider>
  );
}

describe("LogOfflineActivityModal", () => {
  beforeEach(() => {
    logMutate.mockReset();
    fetchPlayerAndCharacter.mockReset();
    gameValue = { player: { is_premium: true }, fetchPlayerAndCharacter };
  });

  it("blocks submission and shows errors when required fields are missing", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.click(screen.getByRole("button", { name: "Log activity" }));

    expect(await screen.findByText("Enter or select a task.")).toBeInTheDocument();
    expect(screen.getByText("Enter a duration greater than zero.")).toBeInTheDocument();
    expect(logMutate).not.toHaveBeenCalled();
  });

  it("submits a valid entry and shows the XP confirmation", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText("Task"), "Write docs");
    await user.type(screen.getByLabelText("Minutes"), "30");

    await user.click(screen.getByRole("button", { name: "Log activity" }));

    await waitFor(() => expect(logMutate).toHaveBeenCalledTimes(1));
    const [payload, callbacks] = logMutate.mock.calls[0];
    expect(payload.name).toBe("Write docs");
    expect(payload.started_at < payload.completed_at).toBe(true);

    act(() => {
      callbacks.onSuccess({
        success: true,
        message: "Activity logged",
        activity: { name: "Write docs" },
        xp_gained: 42,
        xp_eligible_seconds: 1800,
        level_ups: [],
      });
    });

    expect(await screen.findByText("+42 XP awarded")).toBeInTheDocument();
    expect(fetchPlayerAndCharacter).toHaveBeenCalled();
  });

  it("surfaces the backend error message on failure", async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText("Task"), "Write docs");
    await user.type(screen.getByLabelText("Minutes"), "30");
    await user.click(screen.getByRole("button", { name: "Log activity" }));

    await waitFor(() => expect(logMutate).toHaveBeenCalledTimes(1));
    const [, callbacks] = logMutate.mock.calls[0];

    act(() => {
      callbacks.onError(new Error(JSON.stringify({ success: false, message: "Daily limit reached." })));
    });

    expect(await screen.findByText("Daily limit reached.")).toBeInTheDocument();
  });

  it("warns free-tier users that XP won't be awarded", async () => {
    gameValue = { player: { is_premium: false }, fetchPlayerAndCharacter };
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText("Minutes"), "10");

    expect(
      await screen.findByText(
        "This will be recorded, but offline activities only earn XP for Premium accounts."
      )
    ).toBeInTheDocument();
  });
});
