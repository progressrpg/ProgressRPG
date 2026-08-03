import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TooltipProvider } from "../Tooltip/Tooltip";
import TasksPanel from "./TasksPanel";

function renderTasksPanel() {
  return render(
    <TooltipProvider>
      <TasksPanel />
    </TooltipProvider>
  );
}

const mockUseTasks = vi.fn();
const mockUseCreateTask = vi.fn();
const mockUseUpdateTask = vi.fn();
const mockUseDeleteTask = vi.fn();
const createMutate = vi.fn();
const updateMutate = vi.fn();
const deleteMutate = vi.fn();

const navigate = vi.fn();
const startActivity = vi.fn().mockResolvedValue(undefined);
const fetchPlayerAndCharacter = vi.fn();

// TasksPanel pulls navigation, the activity timer and the player from context.
let gameValue: Record<string, unknown>;

vi.mock("../../hooks/useTasks", () => ({
  useTasks: () => mockUseTasks(),
  useCreateTask: () => mockUseCreateTask(),
  useUpdateTask: () => mockUseUpdateTask(),
  useDeleteTask: () => mockUseDeleteTask(),
}));

vi.mock("react-router", () => ({
  useNavigate: () => navigate,
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
      aria-label="new task"
      placeholder={placeholder}
      value={value}
      onChange={(event) => onChange?.(event.target.value)}
    />
  ),
}));

const incompleteTask = {
  id: 1,
  name: "Morning routine",
  is_complete: false,
  completed_at: null,
  created_at: "2026-05-01T08:00:00.000Z",
  last_updated: "2026-05-01T08:00:00.000Z",
  last_worked_on: null,
  total_time: 1800,
  total_records: 3,
};

const completeTask = {
  id: 2,
  name: "Taxes",
  is_complete: true,
  completed_at: "2026-05-03T12:00:00.000Z",
  created_at: "2026-04-01T08:00:00.000Z",
  last_updated: "2026-05-03T12:00:00.000Z",
  last_worked_on: "2026-05-03T12:00:00.000Z",
  total_time: 600,
  total_records: 1,
};

describe("TasksPanel", () => {
  beforeEach(() => {
    createMutate.mockReset();
    updateMutate.mockReset();
    deleteMutate.mockReset();
    navigate.mockReset();
    startActivity.mockClear();
    fetchPlayerAndCharacter.mockReset();
    localStorage.clear();

    gameValue = {
      fetchPlayerAndCharacter,
      activityTimer: { status: "idle", startActivity },
      freeTimerLimitSeconds: 1800,
      player: { is_premium: false },
    };

    mockUseTasks.mockReturnValue({
      isLoading: false,
      data: [incompleteTask, completeTask],
    });
    mockUseCreateTask.mockReturnValue({ mutate: createMutate });
    mockUseUpdateTask.mockReturnValue({ mutate: updateMutate });
    mockUseDeleteTask.mockReturnValue({ mutate: deleteMutate });
  });

  it("hides completed tasks by default", () => {
    renderTasksPanel();

    expect(screen.getByText("Morning routine")).toBeInTheDocument();
    expect(screen.queryByText("Taxes")).not.toBeInTheDocument();
  });

  it("reveals completed tasks and persists the preference when toggled", async () => {
    const user = userEvent.setup();
    renderTasksPanel();

    await user.click(screen.getByRole("button", { name: "Show complete" }));

    expect(screen.getByText("Taxes")).toBeInTheDocument();
    expect(localStorage.getItem("tasks.hideCompleted")).toBe("false");
    // Button label flips once completed tasks are shown.
    expect(screen.getByRole("button", { name: "Hide complete" })).toBeInTheDocument();
  });

  it("respects a persisted 'show complete' preference on mount", () => {
    localStorage.setItem("tasks.hideCompleted", "false");
    renderTasksPanel();

    expect(screen.getByText("Taxes")).toBeInTheDocument();
  });

  it("toggles task completion with the row checkbox", async () => {
    const user = userEvent.setup();
    renderTasksPanel();

    await user.click(
      screen.getByRole("checkbox", { name: "Mark Morning routine as complete" }),
    );

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith(
        { id: 1, data: { is_complete: true, completed_at: expect.any(String) } },
        expect.objectContaining({ onSuccess: expect.any(Function) }),
      );
    });
  });

  it("starts a linked activity and navigates to the timer from the play button", async () => {
    // The play button lives in a hover-revealed row (pointer-events:none until
    // hover), which jsdom can't simulate, so skip the pointer-events guard.
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    renderTasksPanel();

    await user.click(screen.getByRole("button", { name: "Start working on Morning routine" }));

    await waitFor(() => {
      expect(startActivity).toHaveBeenCalledWith({
        text: "Morning routine",
        taskId: 1,
        limitSeconds: 1800,
      });
    });
    expect(navigate).toHaveBeenCalledWith("/timer");
  });

  it("does not start an activity when a timer is already running", async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    gameValue.activityTimer = { status: "active", startActivity };
    renderTasksPanel();

    await user.click(screen.getByRole("button", { name: "Start working on Morning routine" }));

    expect(startActivity).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("edits a task name through the PlayerItemList dialog", async () => {
    const user = userEvent.setup();
    renderTasksPanel();

    // hoverEdit renders the name and a 📝 button with the same label; either opens the dialog.
    await user.click(
      screen.getAllByRole("button", { name: "Edit task Morning routine" })[0],
    );
    const input = screen.getByLabelText("task name");
    await user.clear(input);
    await user.type(input, "Evening routine");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        id: 1,
        data: { name: "Evening routine" },
      });
    });
  });
});
