import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TasksPage from "./TasksPage";

const mockUseTasks = vi.fn();
const mockUseCreateTask = vi.fn();
const mockUseUpdateTask = vi.fn();
const mockUseDeleteTask = vi.fn();
const createMutate = vi.fn();
const updateMutate = vi.fn();
const deleteMutate = vi.fn();

vi.mock("../../hooks/useTasks", () => ({
  useTasks: () => mockUseTasks(),
  useCreateTask: () => mockUseCreateTask(),
  useUpdateTask: () => mockUseUpdateTask(),
  useDeleteTask: () => mockUseDeleteTask(),
}));

describe("TasksPage", () => {
  beforeEach(() => {
    createMutate.mockReset();
    updateMutate.mockReset();
    deleteMutate.mockReset();

    mockUseTasks.mockReturnValue({
      isLoading: false,
      data: [
        { id: 1, name: "Morning routine", is_complete: false, total_time: 1800, total_records: 3 },
      ],
    });
    mockUseCreateTask.mockReturnValue({ mutate: createMutate });
    mockUseUpdateTask.mockReturnValue({ mutate: updateMutate });
    mockUseDeleteTask.mockReturnValue({ mutate: deleteMutate });
  });

  it("toggles task completion with the row checkbox", async () => {
    const user = userEvent.setup();
    render(<TasksPage />);

    await user.click(screen.getByRole("checkbox", { name: "Mark Morning routine as complete" }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        id: 1,
        data: { completed_at: expect.any(String) },
      });
    });
  });

  it("clears completed_at when unchecking a completed task", async () => {
    const user = userEvent.setup();
    mockUseTasks.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 1,
          name: "Morning routine",
          completed_at: "2026-05-03T12:00:00.000Z",
          total_time: 1800,
          total_records: 3,
        },
      ],
    });

    render(<TasksPage />);

    await user.click(screen.getByRole("checkbox", { name: "Mark Morning routine as complete" }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        id: 1,
        data: { completed_at: null },
      });
    });
  });

  it("edits and deletes tasks through PlayerItemList", async () => {
    const user = userEvent.setup();
    render(<TasksPage />);

    await user.click(screen.getByRole("button", { name: "Open task Morning routine" }));
    const input = screen.getByLabelText("task name");
    await user.clear(input);
    await user.type(input, "Evening routine");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        id: 1,
        data: { name: "Evening routine" },
      });
    });

    await user.click(screen.getByRole("button", { name: "Open task Morning routine" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteMutate).toHaveBeenCalledWith(1);
    });
  });
});
