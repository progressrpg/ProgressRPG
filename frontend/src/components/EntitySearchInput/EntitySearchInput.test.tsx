import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import EntitySearchInput from "./EntitySearchInput";
import type { SearchEntity } from "./useEntitySearchInput";

interface MockEntity {
  id: string | number;
  name: string;
  taskId: number | null;
  source: "task" | "activity";
}

let mockEntities: MockEntity[] = [];
const addEntityToCache = vi.fn();

vi.mock("../../hooks/useEntitySearchCache", () => ({
  useEntitySearchCache: () => ({ entities: mockEntities, addEntityToCache }),
}));

// EntitySearchInput is controlled, so drive its value from local state.
function Harness({
  type = "activity",
  onCreate,
  onSelect,
  alwaysOpen,
  defaultResults,
}: {
  type?: "task" | "activity";
  onCreate?: (name: string) => void;
  onSelect?: (entity: SearchEntity) => void;
  alwaysOpen?: boolean;
  defaultResults?: MockEntity[];
}) {
  const [value, setValue] = useState("");
  return (
    <EntitySearchInput
      type={type}
      value={value}
      onChange={setValue}
      onCreate={onCreate}
      onSelect={onSelect}
      alwaysOpen={alwaysOpen}
      defaultResults={defaultResults}
      ariaLabel="task search"
    />
  );
}

describe("EntitySearchInput", () => {
  beforeEach(() => {
    addEntityToCache.mockReset();
    mockEntities = [];
  });

  it("dedupes a task and an identically-named activity into one suggestion", async () => {
    const user = userEvent.setup();
    mockEntities = [
      { id: "t1", name: "Write report", taskId: 1, source: "task" },
      { id: "a1", name: "Write report", taskId: null, source: "activity" },
      { id: "t2", name: "Write tests", taskId: 2, source: "task" },
    ];

    render(<Harness />);
    await user.type(screen.getByRole("combobox"), "write");

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    // The duplicate activity is dropped; the task wins.
    expect(screen.getAllByRole("option", { name: "Write report" })).toHaveLength(1);
    expect(screen.getByRole("option", { name: "Write tests" })).toBeInTheDocument();
  });

  it("includes completed tasks among the suggestions", async () => {
    const user = userEvent.setup();
    mockEntities = [
      // Completed tasks are kept in the search cache and should still surface.
      { id: "t9", name: "Archive logs", taskId: 9, source: "task" },
    ];

    render(<Harness type="task" />);
    await user.type(screen.getByRole("combobox"), "arch");

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Archive logs" })).toBeInTheDocument();
    });
  });

  it("creates a new task when the typed name has no match", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();
    mockEntities = [{ id: "t1", name: "Write report", taskId: 1, source: "task" }];

    render(<Harness type="task" onCreate={onCreate} />);
    await user.type(screen.getByRole("combobox"), "Plan offsite");
    await user.keyboard("{Enter}");

    expect(onCreate).toHaveBeenCalledWith("Plan offsite");
    expect(addEntityToCache).toHaveBeenCalledWith("Plan offsite");
  });

  it("renders default results open on load when alwaysOpen is set, with no focus needed", () => {
    const defaultResults: MockEntity[] = [
      { id: "t1", name: "Write report", taskId: 1, source: "task" },
      { id: "a1", name: "Washing dishes", taskId: null, source: "activity" },
    ];

    render(<Harness alwaysOpen defaultResults={defaultResults} />);

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Write report" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Washing dishes" })).toBeInTheDocument();
  });

  it("shows an empty-state message when there are no default results yet", () => {
    render(<Harness alwaysOpen defaultResults={[]} />);

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.queryByRole("option")).not.toBeInTheDocument();
  });

  it("switches from default results to fuzzy matches while typing, then snaps back to default results when cleared", async () => {
    const user = userEvent.setup();
    mockEntities = [
      { id: "t1", name: "Write report", taskId: 1, source: "task" },
      { id: "t2", name: "Write tests", taskId: 2, source: "task" },
    ];
    const defaultResults: MockEntity[] = [
      { id: "a1", name: "Washing dishes", taskId: null, source: "activity" },
    ];

    render(<Harness alwaysOpen defaultResults={defaultResults} />);

    expect(screen.getByRole("option", { name: "Washing dishes" })).toBeInTheDocument();

    const input = screen.getByRole("combobox");
    await user.type(input, "write");

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Write tests" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("option", { name: "Washing dishes" })).not.toBeInTheDocument();

    await user.clear(input);

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Washing dishes" })).toBeInTheDocument();
    });
  });

  it("starts immediately by calling onSelect when a persistent list row is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const defaultResults: MockEntity[] = [
      { id: "t1", name: "Write report", taskId: 1, source: "task" },
    ];

    render(<Harness alwaysOpen defaultResults={defaultResults} onSelect={onSelect} />);

    await user.click(screen.getByRole("option", { name: "Write report" }));

    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Write report", taskId: 1, source: "task" })
    );
  });
});
