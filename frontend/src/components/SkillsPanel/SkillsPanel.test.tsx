import { render as rtlRender, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TamaguiProvider } from "tamagui";

import SkillsPanel from "./SkillsPanel";
import tamaguiConfig from "../../../tamagui.config";

// SkillsPanel renders Modal via PlayerItemList (#582), which needs a
// TamaguiProvider ancestor - unlike Radix's Dialog.Root, it isn't usable
// standalone. The app root (src/main.tsx) provides this in production;
// tests need their own.
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

  it(
    "edits a skill through PlayerItemList",
    async () => {
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
    },
    // Open/type/tab through a real Tamagui Modal — the default 5000ms
    // budget gets tight under a full parallel suite run (passes standalone;
    // was flaking under CPU contention alongside the storybook/browser project).
    10000,
  );

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
