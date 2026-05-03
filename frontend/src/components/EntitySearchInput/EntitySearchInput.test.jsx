import { useState } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import EntitySearchInput from "./EntitySearchInput";

const mockUseEntitySearchCache = vi.fn();
const addEntityToCache = vi.fn();

vi.mock("../../hooks/useEntitySearchCache", () => ({
  useEntitySearchCache: (...args) => mockUseEntitySearchCache(...args),
}));

function renderSearchInput(overrides = {}) {
  const onSelect = vi.fn();
  const onCreate = vi.fn();

  function Fixture() {
    const [value, setValue] = useState("");

    return (
      <EntitySearchInput
        type="activity"
        value={value}
        onChange={setValue}
        onSelect={onSelect}
        onCreate={onCreate}
        ariaLabel="Activity search"
        {...overrides}
      />
    );
  }

  return {
    onSelect,
    onCreate,
    ...render(<Fixture />),
  };
}

describe("EntitySearchInput", () => {
  beforeEach(() => {
    addEntityToCache.mockReset();
    mockUseEntitySearchCache.mockReturnValue({
      entities: [
        { id: 1, name: "Write docs" },
        { id: 10, name: " write   docs " },
        { id: 2, name: "Write tests" },
        { id: 3, name: "Write changelog" },
        { id: 4, name: "Write release notes" },
        { id: 5, name: "Write email" },
        { id: 6, name: "Write outline" },
        { id: 7, name: "Write plan" },
        { id: 8, name: "Write summary" },
        { id: 9, name: "Write postmortem" },
      ],
      addEntityToCache,
    });
  });

  it("shows fuzzy-search results after the debounce and caps them at eight", async () => {
    const user = userEvent.setup();
    renderSearchInput();

    await user.type(screen.getByRole("textbox", { name: "Activity search" }), "writ");

    await waitFor(() => {
      expect(screen.getAllByRole("option")).toHaveLength(7);
    });

    expect(screen.getByRole("option", { name: "Write docs" })).toBeInTheDocument();
    expect(screen.getAllByRole("option", { name: "Write docs" })).toHaveLength(1);
  });

  it("supports keyboard selection", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderSearchInput();
    const input = screen.getByRole("textbox", { name: "Activity search" });

    await user.type(input, "writ");

    await waitFor(() => {
      expect(screen.getAllByRole("option")).not.toHaveLength(0);
    });

    await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");

    expect(onSelect).toHaveBeenCalledWith({ id: 2, name: "Write tests" });
    expect(input).toHaveValue("Write tests");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("creates a new entity name when enter is pressed without a selection", async () => {
    const user = userEvent.setup();
    const { onCreate } = renderSearchInput();
    const input = screen.getByRole("textbox", { name: "Activity search" });

    await user.clear(input);
    await user.type(input, "Wash dishes");

    await user.keyboard("{Enter}");

    expect(addEntityToCache).toHaveBeenCalledWith("Wash dishes");
    expect(onCreate).toHaveBeenCalledWith("Wash dishes");
    expect(input).toHaveValue("Wash dishes");
  });

  it("closes the dropdown when clicking outside", async () => {
    const user = userEvent.setup();
    renderSearchInput();

    await user.type(screen.getByRole("textbox", { name: "Activity search" }), "writ");

    await waitFor(() => {
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    await user.click(document.body);

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
