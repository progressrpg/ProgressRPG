// SupportFlow/SupportFlowModal.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render as rtlRender, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useReducer } from "react";
import type { Dispatch } from "react";
import { TamaguiProvider } from "tamagui";
import SupportFlowModal from "./SupportFlowModal";
import type { FlowState } from "./SupportFlowModal";
import { supportFlowReducer } from "./supportFlowReducer";
import tamaguiConfig from "../../../tamagui.config";

// SupportFlowModal renders Modal (#582), which needs a TamaguiProvider
// ancestor - unlike Radix's Dialog.Root, it isn't usable standalone. The
// app root (src/main.tsx) provides this in production; tests need their own.
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

const mockUseGame = vi.fn();

vi.mock("../../hooks/useTasks", () => ({
  useTasks: () => ({ data: [] }),
  useUpdateTask: () => ({ mutate: vi.fn() }),
}));

vi.mock("../../hooks/useFeatureFlag", () => ({
  useFeatureFlag: () => false,
}));

vi.mock("../../hooks/useGame", () => ({
  useGame: () => mockUseGame(),
}));

mockUseGame.mockReturnValue({
  player: { is_premium: false, is_tester: false },
  fetchPlayerAndCharacter: vi.fn(),
});

type FlowAction = { type: string; [key: string]: unknown };

// Helper: renders SupportFlowModal with reducer state
function Fixture({
  initialEvent,
  initialEventPayload = {},
  onConfirmActivity = vi.fn(),
}: {
  initialEvent: string;
  initialEventPayload?: Record<string, unknown>;
  onConfirmActivity?: (text?: string) => void;
}) {
  const [state, dispatch] = useReducer(
    supportFlowReducer as unknown as (state: FlowState, action: FlowAction) => FlowState,
    { isOpen: false } as FlowState
  );

  // Fire the opening event once on mount via a button
  return (
    <>
      <button onClick={() => dispatch({ type: initialEvent, ...initialEventPayload })}>Open</button>
      <SupportFlowModal
        state={state}
        dispatch={dispatch as Dispatch<FlowAction>}
        onConfirmActivity={onConfirmActivity}
      />
    </>
  );
}

describe("SupportFlowModal", () => {
  it("renders nothing when modal is closed", () => {
    const state: FlowState = { isOpen: false };
    render(
      <SupportFlowModal
        state={state}
        dispatch={() => {}}
        onConfirmActivity={() => {}}
      />
    );
    // Not container.firstChild - the TamaguiProvider test wrapper always
    // renders its own wrapping element, closed or not.
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens welcome message screen", async () => {
    const user = userEvent.setup();
    render(
      <Fixture
        initialEvent="OPEN_WELCOME_MESSAGE"
        initialEventPayload={{
          loginState: "streak_continues",
          loginStreak: 4,
          loginRewardXp: 16,
        }}
      />
    );
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByRole("heading", { name: "Welcome!" })).toBeInTheDocument();
    expect(
      screen.getByText("Welcome back! Your login streak is now 4 days.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("You earned +16 XP from today's login.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Get support" })
    ).toBeInTheDocument();
  });

  it("renders repeat-login welcome copy", async () => {
    const user = userEvent.setup();
    render(
      <Fixture
        initialEvent="OPEN_WELCOME_MESSAGE"
        initialEventPayload={{ loginState: "already_logged_today", loginStreak: 4 }}
      />
    );
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(
      screen.getByText(
        "Welcome back! You logged in earlier today. You have logged in for 4 days in a row."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/You earned \+\d+ XP from today's login\./)
    ).not.toBeInTheDocument();
  });

  it("opens activity reward screen", async () => {
    const user = userEvent.setup();
    render(
      <Fixture
        initialEvent="OPEN_ACTIVITY_REWARD"
        initialEventPayload={{
          xpGained: "27",
          activityName: "Write tests",
          elapsedSeconds: 90,
        }}
      />
    );
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByText("Activity complete!")).toBeInTheDocument();
    expect(
      screen.getByText('Nice work ⚔️ You spent 1 minute 30 seconds on "Write tests".')
    ).toBeInTheDocument();
    expect(screen.getByText("Total XP gained")).toBeInTheDocument();
    expect(screen.getByText("+27 XP")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Continue with support" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Back to timer" })
    ).toBeInTheDocument();
  });

  it("opens support mode directly to support menu", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_SUPPORT_MODE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByText("How are you feeling?")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Ready for next step" })
    ).toBeInTheDocument();
  });

  it("navigates from welcome message to support menu", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    expect(screen.getByText("How are you feeling?")).toBeInTheDocument();
  });

  it("back from support menu returns to welcome message", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("heading", { name: "Welcome!" })).toBeInTheDocument();
    expect(screen.getByText(/welcome back!/i)).toBeInTheDocument();
  });

  it("back from support menu returns to activity reward", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_ACTIVITY_REWARD" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Continue with support" }));
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Activity complete!")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Continue with support" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Continue with support in/i })
    ).not.toBeInTheDocument();
  });

  it("support mode menu does not show reward back button", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_SUPPORT_MODE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByText("How are you feeling?")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back" })).not.toBeInTheDocument();
  });

  it("back from ready menu returns to support menu", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    expect(screen.getByText("Choose an activity")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Name the tiniest first step now. The activity is writing it down, not doing it yet."
      )
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("How are you feeling?")).toBeInTheDocument();
  });

  it("back from not-ready menu returns to support menu", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "I'm not ready yet" }));
    expect(screen.getByText("Let's support you")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("How are you feeling?")).toBeInTheDocument();
  });

  it("header back from activity input returns to ready menu", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    await user.click(screen.getByRole("button", { name: "Help me choose a task" }));
    expect(screen.getByText("Describe your activity")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Choose an activity")).toBeInTheDocument();
  });

  it("header back works while a task input is focused", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    await user.click(
      screen.getByRole("button", { name: "Help me choose a task" })
    );

    screen.getByRole("textbox", { name: "Task option 1" }).focus();

    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Choose an activity")).toBeInTheDocument();
  });

  it("tiniest-step preset shows examples only and can start without text input", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <Fixture initialEvent="OPEN_WELCOME_MESSAGE" onConfirmActivity={onConfirm} />
    );
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    await user.click(
      screen.getByRole("button", { name: "Write down the tiniest first step" })
    );
    // Should be on examples-only activity screen (no text input)
    expect(screen.getByText("Describe your activity")).toBeInTheDocument();
    expect(
      screen.queryByRole("textbox", { name: "Activity description" })
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Write it down" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("navigates not-ready path to support detail", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_ACTIVITY_REWARD" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Continue with support" }));
    await user.click(
      screen.getByRole("button", { name: "I'm not ready yet" })
    );
    expect(screen.getByText("Let's support you")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Breathing exercise" })
    );
    expect(screen.getByText("Support steps")).toBeInTheDocument();
    expect(screen.getByText("Breathe in slowly for 4 counts.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Back to support menu" })
    ).toBeInTheDocument();
  });

  it("returning from support detail to support menu hides reward back button", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_ACTIVITY_REWARD" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Continue with support" }));
    await user.click(screen.getByRole("button", { name: "I'm not ready yet" }));
    await user.click(
      screen.getByRole("button", { name: "Breathing exercise" })
    );

    await user.click(
      screen.getByRole("button", { name: "Back to support menu" })
    );
    expect(screen.getByText("How are you feeling?")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back" })).not.toBeInTheDocument();
  });

  it("closes modal when close button is clicked", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByRole("heading", { name: "Welcome!" })).toBeInTheDocument();
    await user.click(screen.getByLabelText("Close modal"));
    expect(screen.queryByRole("heading", { name: "Welcome!" })).not.toBeInTheDocument();
  });

  it("close button works while a task input is focused", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    await user.click(
      screen.getByRole("button", { name: "Help me choose a task" })
    );

    screen.getByRole("textbox", { name: "Task option 1" }).focus();

    await user.click(screen.getByLabelText("Close modal"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("priority-three preset shows three task inputs", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    await user.click(
      screen.getByRole("button", { name: "Help me choose a task" })
    );
    expect(screen.getByText("Describe your activity")).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Task option 1" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Task option 2" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: "Task option 3" })
    ).toBeInTheDocument();
  });

  it("priority-three start-this uses selected task text", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <Fixture initialEvent="OPEN_WELCOME_MESSAGE" onConfirmActivity={onConfirm} />
    );
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    await user.click(
      screen.getByRole("button", { name: "Help me choose a task" })
    );
    await user.type(screen.getByRole("textbox", { name: "Task option 2" }), "Send project update");
    await user.click(screen.getAllByRole("button", { name: "Start this" })[1]);
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith("Send project update", undefined);
  });

  it("priority-three randomise starts one of filled tasks", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const randomSpy = vi.spyOn(Math, "random").mockReturnValue(0.9);

    render(
      <Fixture initialEvent="OPEN_WELCOME_MESSAGE" onConfirmActivity={onConfirm} />
    );
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    await user.click(
      screen.getByRole("button", { name: "Help me choose a task" })
    );

    const randomizeButton = screen.getByRole("button", { name: "Randomise and start" });
    expect(randomizeButton).toBeDisabled();

    await user.type(screen.getByRole("textbox", { name: "Task option 1" }), "Pay invoice");
    await user.type(screen.getByRole("textbox", { name: "Task option 3" }), "Review PR");
    expect(randomizeButton).not.toBeDisabled();

    await user.click(randomizeButton);
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith("Review PR", undefined);

    randomSpy.mockRestore();
  });

  it("priority-three randomise remains disabled when empty", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "Ready for next step" }));
    await user.click(
      screen.getByRole("button", { name: "Help me choose a task" })
    );
    expect(
      screen.getByRole("button", { name: "Randomise and start" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Randomise and start" })
    ).toBeDisabled();
  });
});
