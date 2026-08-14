import type { ComponentProps } from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TooltipProvider } from "../Tooltip/Tooltip";
import TasksPanel from "./TasksPanel";

function renderTasksPanel(props: ComponentProps<typeof TasksPanel> = {}) {
  return render(
    <TooltipProvider>
      <TasksPanel {...props} />
    </TooltipProvider>
  );
}

const mockUseTasks = vi.fn();
const mockUseCreateTask = vi.fn();
const mockUseUpdateTask = vi.fn();
const mockUseDeleteTask = vi.fn();
const mockUseNotes = vi.fn();
const mockUseCreateNote = vi.fn();
const createMutate = vi.fn();
const updateMutate = vi.fn();
const deleteMutate = vi.fn();
const createNoteMutate = vi.fn();

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

vi.mock("../../hooks/useNotes", () => ({
  useNotes: () => mockUseNotes(),
  useCreateNote: () => mockUseCreateNote(),
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
  due_at: null,
  parent: null,
  subtask_count: 0,
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
  due_at: null,
  parent: null,
  subtask_count: 0,
  total_time: 600,
  total_records: 1,
};

describe("TasksPanel", () => {
  beforeEach(() => {
    createMutate.mockReset();
    updateMutate.mockReset();
    deleteMutate.mockReset();
    createNoteMutate.mockReset();
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
    mockUseNotes.mockReturnValue({ data: [] });
    mockUseCreateNote.mockReturnValue({ mutate: createNoteMutate });
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

  it("opens the edit dialog for openTaskId on mount", async () => {
    const onOpenTaskHandled = vi.fn();
    renderTasksPanel({ openTaskId: 1, onOpenTaskHandled });

    await waitFor(() => {
      expect(within(screen.getByRole("dialog")).getByDisplayValue("Morning routine")).toBeInTheDocument();
    });
    expect(onOpenTaskHandled).toHaveBeenCalled();
  });

  it("reveals a completed openTaskId even though completed tasks are hidden by default", async () => {
    const onOpenTaskHandled = vi.fn();
    renderTasksPanel({ openTaskId: 2, onOpenTaskHandled });

    await waitFor(() => {
      expect(within(screen.getByRole("dialog")).getByDisplayValue("Taxes")).toBeInTheDocument();
    });
    expect(onOpenTaskHandled).toHaveBeenCalled();
  });

  it("does not show note controls in the edit dialog when onOpenNote is not provided", async () => {
    const user = userEvent.setup();
    renderTasksPanel();

    await user.click(
      screen.getAllByRole("button", { name: "Edit task Morning routine" })[0],
    );

    expect(
      within(screen.getByRole("dialog")).queryByRole("button", { name: "Create note for this task" }),
    ).not.toBeInTheDocument();
  });

  it("offers to create a note for a task with no linked note", async () => {
    const user = userEvent.setup();
    const onOpenNote = vi.fn();
    createNoteMutate.mockImplementation((_data, { onSuccess }) => onSuccess({ id: 9 }));
    renderTasksPanel({ onOpenNote });

    await user.click(
      screen.getAllByRole("button", { name: "Edit task Morning routine" })[0],
    );
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Create note for this task" }),
    );

    expect(createNoteMutate).toHaveBeenCalledWith(
      { title: "Morning routine", body: "", task: 1 },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(onOpenNote).toHaveBeenCalledWith(9);
  });

  it("shows a link to an existing linked note instead of the create button", async () => {
    const user = userEvent.setup();
    const onOpenNote = vi.fn();
    mockUseNotes.mockReturnValue({
      data: [{ id: 3, title: "Routine notes", body: "", player: 1, task: 1 }],
    });
    renderTasksPanel({ onOpenNote });

    await user.click(
      screen.getAllByRole("button", { name: "Edit task Morning routine" })[0],
    );
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "View linked note" }),
    );

    expect(onOpenNote).toHaveBeenCalledWith(3);
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
    await user.tab();

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith(
        { id: 1, data: { name: "Evening routine" } },
        expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
      );
    });
  });

  describe("subtasks", () => {
    const parentTask = {
      id: 3,
      name: "Parent project task",
      is_complete: false,
      completed_at: null,
      created_at: "2026-05-01T08:00:00.000Z",
      last_updated: "2026-05-01T08:00:00.000Z",
      last_worked_on: null,
      due_at: null,
      parent: null,
      subtask_count: 1,
      total_time: 0,
      total_records: 0,
    };

    const childTask = {
      id: 4,
      name: "Child subtask",
      is_complete: false,
      completed_at: null,
      created_at: "2026-05-01T08:05:00.000Z",
      last_updated: "2026-05-01T08:05:00.000Z",
      last_worked_on: null,
      due_at: null,
      parent: 3,
      subtask_count: 0,
      total_time: 0,
      total_records: 0,
    };

    it("renders a subtask as an independent, indented row directly after its parent", () => {
      mockUseTasks.mockReturnValue({
        isLoading: false,
        data: [parentTask, childTask],
      });
      renderTasksPanel();

      const parentButton = screen.getAllByRole("button", { name: "Edit task Parent project task" })[0];
      const childButton = screen.getAllByRole("button", { name: "Edit task Child subtask" })[0];
      expect(parentButton).toBeInTheDocument();
      expect(childButton).toBeInTheDocument();
      // The subtask is its own sibling row, not nested inside the parent's <li>.
      const parentListItem = parentButton.closest("li");
      const childListItem = childButton.closest("li");
      expect(parentListItem).not.toBe(childListItem);
      expect(parentListItem).not.toContainElement(childButton);

      const rows = screen.getAllByRole("listitem");
      expect(rows.indexOf(childListItem!)).toBe(rows.indexOf(parentListItem!) + 1);
    });

    it("hides a completed parent and its subtasks together", () => {
      const completedParent = { ...parentTask, id: 5, is_complete: true, completed_at: "2026-05-02T00:00:00.000Z" };
      const childOfCompletedParent = { ...childTask, id: 6, parent: 5 };
      mockUseTasks.mockReturnValue({
        isLoading: false,
        data: [completedParent, childOfCompletedParent],
      });
      renderTasksPanel();

      expect(screen.queryByText("Parent project task")).not.toBeInTheDocument();
      expect(screen.queryByText("Child subtask")).not.toBeInTheDocument();
    });

    it("opens the task detail modal for a blank draft subtask without creating one yet", async () => {
      const user = userEvent.setup({ pointerEventsCheck: 0 });
      mockUseTasks.mockReturnValue({
        isLoading: false,
        data: [parentTask],
      });
      renderTasksPanel();

      await user.click(screen.getByRole("button", { name: "Add subtask to Parent project task" }));

      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByLabelText("task name")).toHaveValue("");
      expect(createMutate).not.toHaveBeenCalled();
    });

    it("creates the subtask only once its draft name has actually been edited, then opens the persisted task", async () => {
      const user = userEvent.setup({ pointerEventsCheck: 0 });
      const newSubtask = { ...childTask, id: 7, name: "New task" };
      createMutate.mockImplementation((_data, callbacks) => {
        callbacks?.onSuccess?.(newSubtask);
      });
      mockUseTasks.mockReturnValue({
        isLoading: false,
        data: [parentTask],
      });
      const { rerender } = renderTasksPanel();

      await user.click(screen.getByRole("button", { name: "Add subtask to Parent project task" }));
      const dialog = await screen.findByRole("dialog");
      const input = within(dialog).getByLabelText("task name");
      await user.type(input, "New task");
      await user.tab();

      expect(createMutate).toHaveBeenCalledWith(
        { name: "New task", parent: 3 },
        expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
      );

      // The new subtask isn't in `items` until the tasks query refetches with it included.
      mockUseTasks.mockReturnValue({
        isLoading: false,
        data: [parentTask, newSubtask],
      });
      rerender(
        <TooltipProvider>
          <TasksPanel />
        </TooltipProvider>,
      );

      const reopenedDialog = await screen.findByRole("dialog");
      expect(within(reopenedDialog).getByDisplayValue("New task")).toBeInTheDocument();
    });

    it("discards the draft subtask, without creating anything, when its modal is closed unedited", async () => {
      const user = userEvent.setup({ pointerEventsCheck: 0 });
      mockUseTasks.mockReturnValue({
        isLoading: false,
        data: [parentTask],
      });
      renderTasksPanel();

      await user.click(screen.getByRole("button", { name: "Add subtask to Parent project task" }));
      const dialog = await screen.findByRole("dialog");
      await user.click(within(dialog).getByRole("button", { name: "Close" }));

      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });
      expect(createMutate).not.toHaveBeenCalled();
    });

    it("disables the parent picker for a task that already has subtasks", async () => {
      const user = userEvent.setup();
      mockUseTasks.mockReturnValue({
        isLoading: false,
        data: [parentTask, childTask],
      });
      renderTasksPanel();

      await user.click(
        screen.getAllByRole("button", { name: "Edit task Parent project task" })[0],
      );

      expect(screen.getByLabelText("Parent task")).toBeDisabled();
    });
  });

  describe("due date", () => {
    it("commits a due date edit immediately on blur", async () => {
      const user = userEvent.setup();
      renderTasksPanel();

      await user.click(
        screen.getAllByRole("button", { name: "Edit task Morning routine" })[0],
      );

      const dueDateInput = screen.getByLabelText("Due date");
      await user.type(dueDateInput, "2026-06-01");
      await user.tab();

      await waitFor(() => {
        expect(updateMutate).toHaveBeenCalledWith(
          { id: 1, data: { due_at: expect.any(String) } },
          expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
        );
      });
    });

    it("defaults the date to today when only a time is set", async () => {
      const user = userEvent.setup();
      renderTasksPanel();

      await user.click(
        screen.getAllByRole("button", { name: "Edit task Morning routine" })[0],
      );

      const dueTimeInput = screen.getByLabelText("Due time");
      await user.type(dueTimeInput, "0900");
      await user.tab();

      await waitFor(() => {
        expect(updateMutate).toHaveBeenCalledWith(
          { id: 1, data: { due_at: expect.any(String) } },
          expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
        );
      });

      const lastCall = updateMutate.mock.calls.at(-1) as [{ data: { due_at: string } }, unknown];
      const committedDate = new Date(lastCall[0].data.due_at);
      const today = new Date();
      expect(committedDate.getFullYear()).toBe(today.getFullYear());
      expect(committedDate.getMonth()).toBe(today.getMonth());
      expect(committedDate.getDate()).toBe(today.getDate());
    });
  });

  describe("timestamps tooltip", () => {
    it("shows Created/Modified/Completed on click of the clock button", async () => {
      const user = userEvent.setup();
      renderTasksPanel();

      await user.click(
        screen.getAllByRole("button", { name: "Edit task Morning routine" })[0],
      );

      expect(screen.queryByText("Created", { selector: "div" })).not.toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "View task timestamps" }));

      expect(screen.getByText("Created", { selector: "div" })).toBeInTheDocument();
      expect(screen.getByText("Modified", { selector: "div" })).toBeInTheDocument();
      expect(screen.getByText("Completed", { selector: "div" })).toBeInTheDocument();
    });
  });
});
