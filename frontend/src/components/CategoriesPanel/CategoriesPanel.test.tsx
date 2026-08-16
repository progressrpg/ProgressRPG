import { render as rtlRender, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TamaguiProvider } from "tamagui";

import CategoriesPanel from "./CategoriesPanel";
import tamaguiConfig from "../../../tamagui.config";

// CategoriesPanel renders Modal via PlayerItemList (#582), which needs a
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

const mockUseCategories = vi.fn();
const mockUseCreateCategory = vi.fn();
const mockUseUpdateCategory = vi.fn();
const mockUseDeleteCategory = vi.fn();
const createMutate = vi.fn();
const updateMutate = vi.fn();
const deleteMutate = vi.fn();

vi.mock("../../hooks/useCategories", () => ({
  useCategories: () => mockUseCategories(),
  useCreateCategory: () => mockUseCreateCategory(),
  useUpdateCategory: () => mockUseUpdateCategory(),
  useDeleteCategory: () => mockUseDeleteCategory(),
}));

describe("CategoriesPanel", () => {
  beforeEach(() => {
    createMutate.mockReset();
    updateMutate.mockReset();
    deleteMutate.mockReset();

    mockUseCategories.mockReturnValue({
      isLoading: false,
      data: [
        { id: 1, name: "Deep Work", total_xp: 220, total_time: 5400, total_records: 5 },
      ],
    });
    mockUseCreateCategory.mockReturnValue({ mutate: createMutate });
    mockUseUpdateCategory.mockReturnValue({ mutate: updateMutate });
    mockUseDeleteCategory.mockReturnValue({ mutate: deleteMutate });
  });

  it("edits and deletes categories through PlayerItemList", async () => {
    const user = userEvent.setup();
    render(<CategoriesPanel />);

    await user.click(screen.getByRole("button", { name: "Open category Deep Work" }));
    const input = screen.getByLabelText("category name");
    await user.clear(input);
    await user.type(input, "Admin");
    await user.tab();

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith(
        { id: 1, data: { name: "Admin" } },
        expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
      );
    });

    // The modal stays open after an autosave — no explicit Save click to close it.
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteMutate).toHaveBeenCalledWith(1);
    });
  });
});
