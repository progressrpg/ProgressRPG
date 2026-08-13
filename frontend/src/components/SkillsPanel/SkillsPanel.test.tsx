import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SkillsPanel from "./SkillsPanel";

const mockUseSkills = vi.fn();
const mockUseCreateSkill = vi.fn();
const mockUseUpdateSkill = vi.fn();
const mockUseDeleteSkill = vi.fn();
const createMutate = vi.fn();
const updateMutate = vi.fn();
const deleteMutate = vi.fn();

vi.mock("../../hooks/useSkills", () => ({
  useSkills: () => mockUseSkills(),
  useCreateSkill: () => mockUseCreateSkill(),
  useUpdateSkill: () => mockUseUpdateSkill(),
  useDeleteSkill: () => mockUseDeleteSkill(),
}));

describe("SkillsPanel", () => {
  beforeEach(() => {
    createMutate.mockReset();
    updateMutate.mockReset();
    deleteMutate.mockReset();

    mockUseSkills.mockReturnValue({
      isLoading: false,
      data: [
        { id: 1, name: "Writing", level: 2, total_xp: 150, total_time: 3600, total_records: 4 },
      ],
    });
    mockUseCreateSkill.mockReturnValue({ mutate: createMutate });
    mockUseUpdateSkill.mockReturnValue({ mutate: updateMutate });
    mockUseDeleteSkill.mockReturnValue({ mutate: deleteMutate });
  });

  it("edits a skill through PlayerItemList", async () => {
    const user = userEvent.setup();
    render(<SkillsPanel />);

    await user.click(screen.getByRole("button", { name: "Open skill Writing" }));
    const input = screen.getByLabelText("skill name");
    await user.clear(input);
    await user.type(input, "Research");
    await user.tab();

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith(
        { id: 1, data: { name: "Research" } },
        expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
      );
    });
  });

  it("deletes a skill through PlayerItemList", async () => {
    const user = userEvent.setup();
    render(<SkillsPanel />);

    await user.click(screen.getByRole("button", { name: "Open skill Writing" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteMutate).toHaveBeenCalledWith(1);
    });
  });
});
