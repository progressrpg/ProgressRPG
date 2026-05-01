// SupportFlow/SupportFlowModal.test.jsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useReducer } from "react";
import SupportFlowModal from "./SupportFlowModal";
import { supportFlowReducer } from "./supportFlowReducer";

// Helper: renders SupportFlowModal with reducer state
function Fixture({ initialEvent, initialEventPayload = {}, onConfirmActivity = vi.fn() }) {
  const [state, dispatch] = useReducer(supportFlowReducer, { isOpen: false });

  // Fire the opening event once on mount via a button
  return (
    <>
      <button onClick={() => dispatch({ type: initialEvent, ...initialEventPayload })}>Open</button>
      <SupportFlowModal
        state={state}
        dispatch={dispatch}
        onConfirmActivity={onConfirmActivity}
      />
    </>
  );
}

describe("SupportFlowModal", () => {
  it("renders nothing when modal is closed", () => {
    const [state] = [{ isOpen: false }];
    const { container } = render(
      <SupportFlowModal
        state={state}
        dispatch={() => {}}
        onConfirmActivity={() => {}}
      />
    );
    expect(container.firstChild).toBeNull();
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
        "Welcome back! You logged in earlier today. Your login streak is 4 days."
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
      screen.getByRole("button", { name: "Start supported session" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Return to timer" })
    ).not.toBeInTheDocument();
  });

  it("opens support mode directly to support menu", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_SUPPORT_MODE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByText("How are you feeling?")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "I'm ready to start" })
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
    await user.click(screen.getByRole("button", { name: "Start supported session" }));
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText("Activity complete!")).toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
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
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
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
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
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
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
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
    await user.click(screen.getByRole("button", { name: "Start supported session" }));
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
    await user.click(screen.getByRole("button", { name: "Start supported session" }));
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
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
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
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
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
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
    await user.click(
      screen.getByRole("button", { name: "Help me choose a task" })
    );
    await user.type(screen.getByRole("textbox", { name: "Task option 2" }), "Send project update");
    await user.click(screen.getAllByRole("button", { name: "Start this" })[1]);
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith("Send project update");
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
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
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
    expect(onConfirm).toHaveBeenCalledWith("Review PR");

    randomSpy.mockRestore();
  });

  it("priority-three randomise remains disabled when empty", async () => {
    const user = userEvent.setup();
    render(<Fixture initialEvent="OPEN_WELCOME_MESSAGE" />);
    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.click(screen.getByRole("button", { name: "Get support" }));
    await user.click(screen.getByRole("button", { name: "I'm ready to start" }));
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
