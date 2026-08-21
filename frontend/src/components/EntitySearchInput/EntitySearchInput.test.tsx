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
  defaultResults,
  alwaysOpen,
  maxVisibleRows,
  emptyMessage,
}: {
  type?: "task" | "activity";
  onCreate?: (name: string) => void;
  defaultResults?: SearchEntity[];
  alwaysOpen?: boolean;
  maxVisibleRows?: number;
  emptyMessage?: string;
}) {
  const [value, setValue] = useState("");
  return (
    <EntitySearchInput
      type={type}
      value={value}
      onChange={setValue}
      onCreate={onCreate}
      ariaLabel="task search"
      defaultResults={defaultResults}
      alwaysOpen={alwaysOpen}
      maxVisibleRows={maxVisibleRows}
      emptyMessage={emptyMessage}
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

  it("points aria-activedescendant at the option ArrowDown highlights", async () => {
    const user = userEvent.setup();
    mockEntities = [
      { id: "t1", name: "Write report", taskId: 1, source: "task" },
      { id: "t2", name: "Write tests", taskId: 2, source: "task" },
    ];

    render(<Harness type="task" />);
    const combobox = screen.getByRole("combobox");
    await user.type(combobox, "write");

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    expect(combobox).not.toHaveAttribute("aria-activedescendant");

    await user.keyboard("{ArrowDown}");
    const firstOption = screen.getByRole("option", { name: "Write report" });
    expect(firstOption).toHaveAttribute("id");
    expect(combobox).toHaveAttribute("aria-activedescendant", firstOption.id);

    await user.keyboard("{ArrowDown}");
    const secondOption = screen.getByRole("option", { name: "Write tests" });
    expect(combobox).toHaveAttribute("aria-activedescendant", secondOption.id);
  });

  it("does not open a persistent list without alwaysOpen (legacy behaviour unchanged)", () => {
    render(<Harness defaultResults={[{ id: "d1", name: "Default row", taskId: null, source: "activity" }]} />);

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("shows defaultResults as a persistent list when alwaysOpen is set and the query is blank", () => {
    render(
      <Harness
        alwaysOpen
        defaultResults={[
          { id: "d1", name: "Washing dishes", taskId: null, source: "activity" },
          { id: "d2", name: "Ship it", taskId: 7, source: "task" },
        ]}
      />
    );

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Washing dishes" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Ship it" })).toBeInTheDocument();
  });

  it("switches from defaultResults to Fuse results once a query is typed", async () => {
    const user = userEvent.setup();
    mockEntities = [{ id: "a1", name: "Write report", taskId: null, source: "activity" }];

    render(
      <Harness
        alwaysOpen
        defaultResults={[{ id: "d1", name: "Washing dishes", taskId: null, source: "activity" }]}
      />
    );

    expect(screen.getByRole("option", { name: "Washing dishes" })).toBeInTheDocument();

    await user.type(screen.getByRole("combobox"), "write");

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Write report" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("option", { name: "Washing dishes" })).not.toBeInTheDocument();
  });

  it("caps combined rows to maxVisibleRows", () => {
    render(
      <Harness
        alwaysOpen
        maxVisibleRows={2}
        defaultResults={[
          { id: "d1", name: "Row one", taskId: null, source: "activity" },
          { id: "d2", name: "Row two", taskId: null, source: "activity" },
          { id: "d3", name: "Row three", taskId: null, source: "activity" },
        ]}
      />
    );

    expect(screen.getAllByRole("option")).toHaveLength(2);
  });

  it("shows emptyMessage instead of the list when alwaysOpen has no rows", () => {
    render(<Harness alwaysOpen defaultResults={[]} emptyMessage="Nothing yet" />);

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(screen.getByText("Nothing yet")).toBeInTheDocument();
  });
});
