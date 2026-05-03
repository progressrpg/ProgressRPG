import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CategoriesPage from "./CategoriesPage";

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

describe("CategoriesPage", () => {
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
    render(<CategoriesPage />);

    await user.click(screen.getByRole("button", { name: "Open category Deep Work" }));
    const input = screen.getByLabelText("category name");
    await user.clear(input);
    await user.type(input, "Admin");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(updateMutate).toHaveBeenCalledWith({
        id: 1,
        data: { name: "Admin" },
      });
    });

    await user.click(screen.getByRole("button", { name: "Open category Deep Work" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteMutate).toHaveBeenCalledWith(1);
    });
  });
});
