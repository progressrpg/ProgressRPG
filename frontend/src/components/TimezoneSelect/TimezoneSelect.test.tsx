import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import TimezoneSelect from "./TimezoneSelect";
import type { TimezoneChoice } from "../../types/api";

const options: TimezoneChoice[] = [
  { value: "UTC", label: "UTC" },
  { value: "Europe/London", label: "Europe/London" },
  { value: "America/New_York", label: "America/New York" },
];

// TimezoneSelect is controlled by value/onChange, so tests drive the value
// from local state, same as the app would.
function Harness({ initialValue = "UTC" }: { initialValue?: string }) {
  const [value, setValue] = useState(initialValue);
  return (
    <TimezoneSelect
      options={options}
      value={value}
      onChange={setValue}
      ariaLabel="Timezone"
    />
  );
}

describe("TimezoneSelect", () => {
  it("shows the selected timezone's label in the input", () => {
    render(<Harness />);

    expect(screen.getByRole("combobox", { name: "Timezone" })).toHaveValue("UTC");
  });

  it("opens a listbox of options on focus", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("combobox", { name: "Timezone" }));

    expect(screen.getByRole("listbox")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Europe/London" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "America/New York" })).toBeInTheDocument();
  });

  it("filters options as the user types", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    const combobox = screen.getByRole("combobox", { name: "Timezone" });
    await user.click(combobox);
    await user.clear(combobox);
    await user.type(combobox, "london");

    expect(screen.getByRole("option", { name: "Europe/London" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "UTC" })).not.toBeInTheDocument();
  });

  it("commits a selection on click and updates the displayed value", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("combobox", { name: "Timezone" }));
    await user.click(screen.getByRole("option", { name: "Europe/London" }));

    expect(screen.getByRole("combobox", { name: "Timezone" })).toHaveValue(
      "Europe/London"
    );
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("keeps a committed selection after clicking away, rather than reverting to the value from mount", async () => {
    // Regression test: the outside-click listener used to be captured once
    // on mount and never refreshed, so it always reverted to whatever the
    // *initial* value was (here "UTC") on every later blur, no matter what
    // had since been selected.
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("combobox", { name: "Timezone" }));
    await user.click(screen.getByRole("option", { name: "Europe/London" }));
    await user.click(document.body);

    expect(screen.getByRole("combobox", { name: "Timezone" })).toHaveValue(
      "Europe/London"
    );
  });

  it("commits the highlighted option on Enter after arrow-key navigation", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    const combobox = screen.getByRole("combobox", { name: "Timezone" });
    await user.click(combobox);
    await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");

    expect(combobox).toHaveValue("Europe/London");
  });

  it("reverts an abandoned query on Escape without calling onChange", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <TimezoneSelect
        options={options}
        value="UTC"
        onChange={handleChange}
        ariaLabel="Timezone"
      />
    );

    const combobox = screen.getByRole("combobox", { name: "Timezone" });
    await user.click(combobox);
    await user.clear(combobox);
    await user.type(combobox, "nowhere");
    await user.keyboard("{Escape}");

    expect(combobox).toHaveValue("UTC");
    expect(handleChange).not.toHaveBeenCalled();
  });

  it("shows timezones past the first 50 alphabetically when unfiltered", async () => {
    // Regression test: the list used to be capped at 50 options even when
    // not actively filtering, so a user browsing the full IANA list (~400
    // entries) could never scroll past "Africa/*" to reach "America/*" etc.
    const manyOptions: TimezoneChoice[] = Array.from({ length: 400 }, (_, i) => ({
      value: `Zone/${i.toString().padStart(3, "0")}`,
      label: `Zone/${i.toString().padStart(3, "0")}`,
    }));
    const user = userEvent.setup();
    render(
      <TimezoneSelect
        options={manyOptions}
        value="Zone/000"
        onChange={() => {}}
        ariaLabel="Timezone"
      />
    );

    await user.click(screen.getByRole("combobox", { name: "Timezone" }));

    expect(screen.getByRole("option", { name: "Zone/399" })).toBeInTheDocument();
  });

  it("does not open the dropdown when disabled", async () => {
    const user = userEvent.setup();
    render(
      <TimezoneSelect
        options={options}
        value="UTC"
        onChange={() => {}}
        ariaLabel="Timezone"
        disabled
      />
    );

    await user.click(screen.getByRole("combobox", { name: "Timezone" }));

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
