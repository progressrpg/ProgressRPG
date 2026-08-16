import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TimerNoteField from "./TimerNoteField";

const mockUseTimerNote = vi.fn();
const mockSetValue = vi.fn();
const mockSave = vi.fn();

vi.mock("../../hooks/useTimerNote", () => ({
  useTimerNote: (...args: unknown[]) => mockUseTimerNote(...args),
}));

describe("TimerNoteField", () => {
  beforeEach(() => {
    mockUseTimerNote.mockReset();
    mockSetValue.mockReset();
    mockSave.mockReset();
    mockUseTimerNote.mockReturnValue({ value: "", setValue: mockSetValue, save: mockSave, enabled: true });
  });

  it("renders nothing when there's nothing to link the note to", () => {
    mockUseTimerNote.mockReturnValue({ value: "", setValue: mockSetValue, save: mockSave, enabled: false });

    const { container } = render(<TimerNoteField taskId={null} activityId={null} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("passes the linked task/activity through to the hook", () => {
    render(<TimerNoteField taskId={5} activityId={null} />);

    expect(mockUseTimerNote).toHaveBeenCalledWith({ taskId: 5, activityId: null });
  });

  it("shows the current note value", () => {
    mockUseTimerNote.mockReturnValue({
      value: "left off here",
      setValue: mockSetValue,
      save: mockSave,
      enabled: true,
    });

    render(<TimerNoteField taskId={null} activityId={7} />);

    expect(screen.getByLabelText("Note for what you're timing")).toHaveValue("left off here");
  });

  it("saves on blur", async () => {
    const user = userEvent.setup();
    render(<TimerNoteField taskId={5} activityId={null} />);

    const field = screen.getByLabelText("Note for what you're timing");
    await user.click(field);
    await user.type(field, "a note");
    await user.tab();

    expect(mockSave).toHaveBeenCalled();
  });

  it("updates the hook's value as the user types", async () => {
    const user = userEvent.setup();
    render(<TimerNoteField taskId={5} activityId={null} />);

    await user.type(screen.getByLabelText("Note for what you're timing"), "x");

    expect(mockSetValue).toHaveBeenCalled();
  });
});
