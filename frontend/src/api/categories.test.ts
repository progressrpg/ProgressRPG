import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createCategory,
  deleteCategory,
  fetchCategories,
  fetchCategory,
  updateCategory,
} from "./categories";
import { apiFetch } from "../utils/api";
import type { Category } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchCategories", () => {
  it("unwraps the paginated results", async () => {
    const categories = [{ id: 1 }] as Category[];
    mockedApiFetch.mockResolvedValueOnce({ results: categories });

    const result = await fetchCategories();

    expect(mockedApiFetch).toHaveBeenCalledWith("/categories/");
    expect(result).toBe(categories);
  });
});

describe("fetchCategory", () => {
  it("fetches a single category by id", async () => {
    const category = { id: 5 } as Category;
    mockedApiFetch.mockResolvedValueOnce(category);

    const result = await fetchCategory(5);

    expect(mockedApiFetch).toHaveBeenCalledWith("/categories/5/");
    expect(result).toBe(category);
  });
});

describe("createCategory", () => {
  it("posts category data", async () => {
    const created = { id: 1 } as Category;
    mockedApiFetch.mockResolvedValueOnce(created);

    const result = await createCategory({ name: "New" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/categories/", {
      method: "POST",
      body: JSON.stringify({ name: "New" }),
    });
    expect(result).toBe(created);
  });
});

describe("updateCategory", () => {
  it("patches category data by id", async () => {
    const updated = { id: 2 } as Category;
    mockedApiFetch.mockResolvedValueOnce(updated);

    const result = await updateCategory(2, { name: "Updated" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/categories/2/", {
      method: "PATCH",
      body: JSON.stringify({ name: "Updated" }),
    });
    expect(result).toBe(updated);
  });
});

describe("deleteCategory", () => {
  it("deletes a category by id", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await deleteCategory(3);

    expect(mockedApiFetch).toHaveBeenCalledWith("/categories/3/", {
      method: "DELETE",
    });
  });
});
