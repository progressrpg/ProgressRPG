import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NotesPanel from "./NotesPanel";

const mockUseNotes = vi.fn();
const mockUseCreateNote = vi.fn();
const mockUseUpdateNote = vi.fn();
const mockUseDeleteNote = vi.fn();
const mockUseTasks = vi.fn();
const createMutate = vi.fn();
const updateMutate = vi.fn();
const deleteMutate = vi.fn();

vi.mock("../../hooks/useNotes", () => ({
  useNotes: () => mockUseNotes(),
  useCreateNote: () => mockUseCreateNote(),
  useUpdateNote: () => mockUseUpdateNote(),
  useDeleteNote: () => mockUseDeleteNote(),
}));

vi.mock("../../hooks/useTasks", () => ({
  useTasks: () => mockUseTasks(),
}));

const note = {
  id: 1,
  title: "Groceries",
  body: "Milk, eggs, bread",
  player: 1,
  task: null,
  created_at: "2026-05-01T08:00:00.000Z",
  last_updated: "2026-05-01T08:00:00.000Z",
};

const task = { id: 5, name: "Ship it" };

describe("NotesPanel", () => {
  beforeEach(() => {
    createMutate.mockReset();
    updateMutate.mockReset();
    deleteMutate.mockReset();

    mockUseNotes.mockReturnValue({ isLoading: false, data: [note] });
    mockUseTasks.mockReturnValue({ data: [task] });
    mockUseCreateNote.mockReturnValue({ mutate: createMutate });
    mockUseUpdateNote.mockReturnValue({ mutate: updateMutate });
    mockUseDeleteNote.mockReturnValue({ mutate: deleteMutate });
  });

  it("renders existing notes with a body preview", () => {
    render(<NotesPanel />);

    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("Milk, eggs, bread")).toBeInTheDocument();
  });

  it("creates a note with the add form", async () => {
    const user = userEvent.setup();
    render(<NotesPanel />);

    await user.type(screen.getByPlaceholderText("New note title"), "Trip plan");
    await user.type(screen.getByLabelText("new note body"), "Pack bags");
    await user.click(screen.getByRole("button", { name: "Add note" }));

    await waitFor(() => {
      expect(createMutate).toHaveBeenCalledWith({
        title: "Trip plan",
        body: "Pack bags",
        task: null,
      });
    });
  });

  it("edits a note's title and body", async () => {
    const user = userEvent.setup();
    render(<NotesPanel />);

    await user.click(screen.getByRole("button", { name: "Open note Groceries" }));

    const titleInput = screen.getByLabelText("Title");
    await user.clear(titleInput);
    await user.type(titleInput, "Weekly groceries");

    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        id: 1,
        data: { title: "Weekly groceries", body: "Milk, eggs, bread", task: null },
      });
    });
  });

  it("does not offer a way to link a note to a task", async () => {
    const user = userEvent.setup();
    render(<NotesPanel />);

    expect(screen.queryByLabelText("Attach to task")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open note Groceries" }));

    expect(screen.queryByLabelText("Linked task")).not.toBeInTheDocument();
  });

  it("shows the linked task in the edit modal when one is set", async () => {
    const user = userEvent.setup();
    mockUseNotes.mockReturnValue({ isLoading: false, data: [{ ...note, task: 5 }] });
    render(<NotesPanel />);

    await user.click(screen.getByRole("button", { name: "Open note Groceries" }));

    expect(within(screen.getByRole("dialog")).getByText("Linked task: Ship it")).toBeInTheDocument();
  });

  it("opens the edit dialog for openNoteId on mount and reports it handled", async () => {
    const onOpenNoteHandled = vi.fn();
    render(<NotesPanel openNoteId={1} onOpenNoteHandled={onOpenNoteHandled} />);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toHaveValue("Groceries");
    expect(onOpenNoteHandled).toHaveBeenCalled();
  });

  it("deletes a note after confirming", async () => {
    const user = userEvent.setup();
    render(<NotesPanel />);

    await user.click(screen.getByRole("button", { name: "Open note Groceries" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteMutate).toHaveBeenCalledWith(1);
    });
  });

  it("shows an empty state when there are no notes", () => {
    mockUseNotes.mockReturnValue({ isLoading: false, data: [] });
    render(<NotesPanel />);

    expect(screen.getByText("No notes yet.")).toBeInTheDocument();
  });
});
