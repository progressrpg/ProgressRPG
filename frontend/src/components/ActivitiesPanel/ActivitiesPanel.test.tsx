import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ActivitiesPanel from "./ActivitiesPanel";

const mockUseActivities = vi.fn();
const mockUseDeleteActivity = vi.fn();
const mockUseUpdateActivity = vi.fn();
const deleteMutate = vi.fn();
const updateMutate = vi.fn();

vi.mock("../../hooks/useActivities", () => ({
  useActivities: () => mockUseActivities(),
  useDeleteActivity: () => mockUseDeleteActivity(),
  useUpdateActivity: () => mockUseUpdateActivity(),
}));

describe("ActivitiesPanel", () => {
  beforeEach(() => {
    deleteMutate.mockReset();
    updateMutate.mockReset();

    mockUseActivities.mockReturnValue({
      isLoading: false,
      data: [
        {
          id: 1,
          name: "Write docs",
          duration: 900,
          xp_gained: 15,
          completed_at: new Date().toISOString(),
        },
      ],
    });
    mockUseDeleteActivity.mockReturnValue({ mutate: deleteMutate });
    mockUseUpdateActivity.mockReturnValue({ mutate: updateMutate });
  });

  it("renders activities and delegates edit through PlayerItemList", async () => {
    const user = userEvent.setup();
    render(<ActivitiesPanel />);

    expect(screen.getByText("Write docs")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open activity Write docs" }));
    const input = screen.getByLabelText("activity name");
    await user.clear(input);
    await user.type(input, "Write tests");
    await user.tab();

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith(
        { activityId: 1, data: { name: "Write tests" } },
        expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
      );
    });
  });

  it("delegates delete confirmation through PlayerItemList", async () => {
    const user = userEvent.setup();
    render(<ActivitiesPanel />);

    await user.click(screen.getByRole("button", { name: "Open activity Write docs" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteMutate).toHaveBeenCalledWith(1);
    });
  });
});
