import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectsPage from "./ProjectsPage";

const mockUseProjects = vi.fn();
const mockUseCreateProject = vi.fn();
const mockUseUpdateProject = vi.fn();
const mockUseDeleteProject = vi.fn();
const createMutate = vi.fn();
const updateMutate = vi.fn();
const deleteMutate = vi.fn();

vi.mock("../../hooks/useProjects", () => ({
  useProjects: () => mockUseProjects(),
  useCreateProject: () => mockUseCreateProject(),
  useUpdateProject: () => mockUseUpdateProject(),
  useDeleteProject: () => mockUseDeleteProject(),
}));

describe("ProjectsPage", () => {
  beforeEach(() => {
    createMutate.mockReset();
    updateMutate.mockReset();
    deleteMutate.mockReset();

    mockUseProjects.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 1,
          name: "Website overhaul",
          description: "Refresh the marketing site",
          total_time: 5400,
          total_records: 6,
          completed_at: null,
        },
      ],
    });
    mockUseCreateProject.mockReturnValue({ mutate: createMutate });
    mockUseUpdateProject.mockReturnValue({ mutate: updateMutate });
    mockUseDeleteProject.mockReturnValue({ mutate: deleteMutate });
  });

  it("creates a project", async () => {
    const user = userEvent.setup();
    render(<ProjectsPage />);

    await user.type(screen.getByRole("textbox"), "New client portal");
    await user.click(screen.getByRole("button", { name: /add project/i }));

    await waitFor(() => {
      expect(createMutate).toHaveBeenCalledWith({ name: "New client portal" });
    });
  });

  it("toggles project completion with the row checkbox", async () => {
    const user = userEvent.setup();
    render(<ProjectsPage />);

    await user.click(screen.getByRole("checkbox", { name: "Mark Website overhaul as complete" }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        id: 1,
        data: { completed_at: expect.any(String) },
      });
    });
  });

  it("edits and deletes projects through PlayerItemList", async () => {
    const user = userEvent.setup();
    render(<ProjectsPage />);

    await user.click(screen.getByRole("button", { name: "Open project Website overhaul" }));
    const input = screen.getByLabelText("project name");
    await user.clear(input);
    await user.type(input, "Platform refresh");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        id: 1,
        data: { name: "Platform refresh" },
      });
    });

    await user.click(screen.getByRole("button", { name: "Open project Website overhaul" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteMutate).toHaveBeenCalledWith(1);
    });
  });
});
