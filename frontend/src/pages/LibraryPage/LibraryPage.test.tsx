import { render as rtlRender, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TamaguiProvider } from "tamagui";

import LibraryPage from "./LibraryPage";
import tamaguiConfig from "../../../tamagui.config";

// LibraryPage renders Tabs (#584), which needs a TamaguiProvider ancestor -
// unlike Radix's Tabs.Root, it isn't usable standalone. The app root
// (src/main.tsx) provides this in production; tests need their own.
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

const mockUseFeatureFlag = vi.fn();

vi.mock("../../hooks/useFeatureFlag", () => ({
  useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
}));

vi.mock("../../components/TasksPanel/TasksPanel", () => ({
  default: ({
    openTaskId,
    onOpenTaskHandled,
    onOpenNote,
  }: {
    openTaskId: number | null;
    onOpenTaskHandled: () => void;
    onOpenNote: (noteId: number) => void;
  }) => (
    <div data-testid="tasks-panel">
      Tasks panel (open task: {openTaskId ?? "none"})
      <button onClick={onOpenTaskHandled}>Clear open task</button>
      <button onClick={() => onOpenNote(42)}>Open note 42</button>
    </div>
  ),
}));

vi.mock("../../components/ActivitiesPanel/ActivitiesPanel", () => ({
  default: () => <div data-testid="activities-panel">Activities panel</div>,
}));

vi.mock("../../components/SkillsPanel/SkillsPanel", () => ({
  default: () => <div data-testid="skills-panel">Skills panel</div>,
}));

vi.mock("../../components/NotesPanel/NotesPanel", () => ({
  default: ({
    openNoteId,
    onOpenNoteHandled,
    onOpenTask,
  }: {
    openNoteId: number | null;
    onOpenNoteHandled: () => void;
    onOpenTask: (taskId: number) => void;
  }) => (
    <div data-testid="notes-panel">
      Notes panel (open note: {openNoteId ?? "none"})
      <button onClick={onOpenNoteHandled}>Clear open note</button>
      <button onClick={() => onOpenTask(7)}>Open task 7</button>
    </div>
  ),
}));

vi.mock("../../components/ComingSoonPanel/ComingSoonPanel", () => ({
  default: ({ itemLabelPlural }: { itemLabelPlural: string }) => (
    <div data-testid="coming-soon-panel">{itemLabelPlural} coming soon</div>
  ),
}));

describe("LibraryPage", () => {
  describe("when all feature flags are enabled", () => {
    beforeEach(() => {
      mockUseFeatureFlag.mockReturnValue(true);
    });

    it("defaults to the Activities tab, rendering ActivitiesPanel", () => {
      render(<LibraryPage />);

      expect(screen.getByRole("heading", { name: "Your library" })).toBeInTheDocument();
      expect(screen.getByTestId("activities-panel")).toBeInTheDocument();
      expect(screen.queryByTestId("tasks-panel")).not.toBeInTheDocument();
    });

    it("switches to the Tasks tab, rendering TasksPanel", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Tasks" }));

      expect(screen.getByTestId("tasks-panel")).toBeInTheDocument();
      expect(screen.queryByTestId("activities-panel")).not.toBeInTheDocument();
    });

    it("switches to the Skills tab, rendering SkillsPanel", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Skills" }));

      expect(screen.getByTestId("skills-panel")).toBeInTheDocument();
      expect(screen.queryByTestId("coming-soon-panel")).not.toBeInTheDocument();
    });

    it("does not render Projects or Categories tabs", () => {
      render(<LibraryPage />);

      expect(screen.queryByRole("tab", { name: "Projects" })).not.toBeInTheDocument();
      expect(screen.queryByRole("tab", { name: "Categories" })).not.toBeInTheDocument();
    });

    it("switches to the Notes tab when a note is opened from the Tasks panel", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Tasks" }));
      await user.click(screen.getByRole("button", { name: "Open note 42" }));

      expect(screen.getByTestId("notes-panel")).toHaveTextContent("open note: 42");
      expect(screen.queryByTestId("tasks-panel")).not.toBeInTheDocument();
    });

    it("switches to the Tasks tab when a task is opened from the Notes panel", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Notes" }));
      await user.click(screen.getByRole("button", { name: "Open task 7" }));

      expect(screen.getByTestId("tasks-panel")).toHaveTextContent("open task: 7");
      expect(screen.queryByTestId("notes-panel")).not.toBeInTheDocument();
    });

    it("clears the pending open-task id once TasksPanel reports it handled", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Notes" }));
      await user.click(screen.getByRole("button", { name: "Open task 7" }));
      expect(screen.getByTestId("tasks-panel")).toHaveTextContent("open task: 7");

      await user.click(screen.getByRole("button", { name: "Clear open task" }));
      expect(screen.getByTestId("tasks-panel")).toHaveTextContent("open task: none");
    });

    it("clears the pending open-note id once NotesPanel reports it handled", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Tasks" }));
      await user.click(screen.getByRole("button", { name: "Open note 42" }));
      expect(screen.getByTestId("notes-panel")).toHaveTextContent("open note: 42");

      await user.click(screen.getByRole("button", { name: "Clear open note" }));
      expect(screen.getByTestId("notes-panel")).toHaveTextContent("open note: none");
    });
  });

  describe("when a tab's feature flag is disabled", () => {
    beforeEach(() => {
      mockUseFeatureFlag.mockReturnValue(false);
    });

    it("still shows the Tasks tab but renders a coming-soon notice", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Tasks" }));

      expect(screen.queryByTestId("tasks-panel")).not.toBeInTheDocument();
      expect(screen.getByTestId("coming-soon-panel")).toHaveTextContent("tasks coming soon");
    });

    it("still shows the Skills tab but renders a coming-soon notice", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Skills" }));

      expect(screen.queryByTestId("skills-panel")).not.toBeInTheDocument();
      expect(screen.getByTestId("coming-soon-panel")).toHaveTextContent("skills coming soon");
    });

    it("still shows the Notes tab but renders a coming-soon notice", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Notes" }));

      expect(screen.queryByTestId("notes-panel")).not.toBeInTheDocument();
      expect(screen.getByTestId("coming-soon-panel")).toHaveTextContent("notes coming soon");
    });

    it("always renders the Activities tab regardless of flags", async () => {
      const user = userEvent.setup();
      render(<LibraryPage />);

      await user.click(screen.getByRole("tab", { name: "Activities" }));

      expect(screen.getByTestId("activities-panel")).toBeInTheDocument();
    });
  });
});
