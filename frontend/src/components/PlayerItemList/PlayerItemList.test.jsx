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
});
