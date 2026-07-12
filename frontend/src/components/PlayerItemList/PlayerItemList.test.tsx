import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import PlayerItemList from "./PlayerItemList";

describe("PlayerItemList", () => {
  const items = [
    {
      id: 1,
      name: "Write docs",
      detail: "Duration: 15m • 15 XP gained",
    },
  ];

  it("renders items through the shared list wrapper", () => {
    render(
      <PlayerItemList
        items={items}
        itemLabel="activity"
        renderItemMeta={(item) => item.detail}
      />,
    );

    expect(screen.getByText("Write docs")).toBeInTheDocument();
    expect(screen.getByText("Duration: 15m • 15 XP gained")).toBeInTheDocument();
  });

  it("opens the edit modal and saves a trimmed name", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();

    render(
      <PlayerItemList
        items={items}
        itemLabel="activity"
        onEdit={onEdit}
        renderEditSummary={() => "Duration: 15m • Completed: 09:00 AM • 15 XP gained"}
        />,
    );

    await user.click(screen.getByRole("button", { name: "Open activity Write docs" }));
    const input = screen.getByLabelText("activity name");
    await user.clear(input);
    await user.type(input, "  Deep work  ");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(onEdit).toHaveBeenCalledWith(items[0], "Deep work");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the delete modal and confirms deletion", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(
      <PlayerItemList
        items={items}
        itemLabel="activity"
        onDelete={onDelete}
        />,
    );

    await user.click(screen.getByRole("button", { name: "Open activity Write docs" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));

    expect(onDelete).toHaveBeenCalledWith(items[0]);
  });

  it("shows item details inside the modal", async () => {
    const user = userEvent.setup();

    render(
      <PlayerItemList
        items={items}
        itemLabel="activity"
        renderEditSummary={(item) => item.detail}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Open activity Write docs" }));

    expect(screen.getByText("Duration: 15m • 15 XP gained")).toBeInTheDocument();
  });

  describe("generic sorting and filtering", () => {
    const sortableItems = [
      { id: 1, name: "Banana", done: false },
      { id: 2, name: "Apple", done: true },
    ];

    const sortOptions = [
      // First option is the default; a no-op comparator preserves input order.
      { key: "created", label: "Created", compareFn: () => 0 },
      {
        key: "name",
        label: "Name",
        compareFn: (a: (typeof sortableItems)[number], b: (typeof sortableItems)[number]) =>
          a.name.localeCompare(b.name),
      },
    ];

    const itemOrder = () =>
      screen
        .getAllByRole("button", { name: /^Open task / })
        .map((button) => button.getAttribute("aria-label"));

    it("keeps input order under the default sort option", () => {
      render(
        <PlayerItemList items={sortableItems} itemLabel="task" sortOptions={sortOptions} />,
      );

      expect(itemOrder()).toEqual(["Open task Banana", "Open task Apple"]);
    });

    it("reorders items when a different sort option is chosen", async () => {
      const user = userEvent.setup();
      render(
        <PlayerItemList items={sortableItems} itemLabel="task" sortOptions={sortOptions} />,
      );

      await user.selectOptions(screen.getByRole("combobox"), "name");

      expect(itemOrder()).toEqual(["Open task Apple", "Open task Banana"]);
    });

    it("applies the active filter predicate", async () => {
      const user = userEvent.setup();
      render(
        <PlayerItemList
          items={sortableItems}
          itemLabel="task"
          filterOptions={[
            { key: "all", label: "All", predicate: () => true },
            { key: "incomplete", label: "Incomplete", predicate: (item) => !item.done },
          ]}
        />,
      );

      // Default filter ("All") shows everything.
      expect(screen.getByText("Banana")).toBeInTheDocument();
      expect(screen.getByText("Apple")).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Incomplete" }));

      expect(screen.getByText("Banana")).toBeInTheDocument();
      expect(screen.queryByText("Apple")).not.toBeInTheDocument();
    });
  });

  describe("getChildren nested rendering", () => {
    const parent = { id: 10, name: "Parent task" };
    const child = { id: 11, name: "Child task" };
    const flatItems = [parent, child];

    it("renders children nested under their parent without a top-level row", () => {
      render(
        <PlayerItemList
          items={flatItems}
          itemLabel="task"
          getChildren={(item) => (item.id === 10 ? [child] : undefined)}
        />,
      );

      expect(screen.getByRole("button", { name: "Open task Parent task" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Open task Child task" })).toBeInTheDocument();
      // The child is not rendered as its own top-level list item.
      expect(screen.getAllByRole("button", { name: /^Open task / })).toHaveLength(2);
    });

    it("is unaffected when getChildren is not passed (ProjectsPanel-style usage)", () => {
      render(<PlayerItemList items={flatItems} itemLabel="task" />);

      // Without getChildren both items render as independent top-level rows.
      expect(screen.getAllByRole("button", { name: /^Open task / })).toHaveLength(2);
      expect(screen.getByRole("button", { name: "Open task Parent task" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Open task Child task" })).toBeInTheDocument();
    });
  });
});
