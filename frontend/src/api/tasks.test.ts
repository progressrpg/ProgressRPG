import { afterEach, describe, expect, it, vi } from "vitest";

import { createTask, deleteTask, fetchTask, fetchTasks, updateTask } from "./tasks";
import { apiFetch } from "../utils/api";
import type { PaginatedResponse, Task } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

function page(results: Task[], next: string | null): PaginatedResponse<Task> {
  return { count: results.length, next, previous: null, results };
}

describe("fetchTasks", () => {
  it("returns all results when there is a single page", async () => {
    const tasks = [{ id: 1 }, { id: 2 }] as Task[];
    mockedApiFetch.mockResolvedValueOnce(page(tasks, null));

    const result = await fetchTasks();

    expect(result).toEqual(tasks);
    expect(mockedApiFetch).toHaveBeenCalledTimes(1);
    expect(mockedApiFetch).toHaveBeenCalledWith("/tasks/");
  });

  it("follows pagination, forwarding the next page's query params", async () => {
    const first = [{ id: 1 }] as Task[];
    const second = [{ id: 2 }] as Task[];
    mockedApiFetch
      .mockResolvedValueOnce(page(first, "https://api.example.com/api/v1/tasks/?page=2"))
      .mockResolvedValueOnce(page(second, null));

    const result = await fetchTasks();

    expect(result).toEqual([...first, ...second]);
    expect(mockedApiFetch).toHaveBeenNthCalledWith(1, "/tasks/");
    expect(mockedApiFetch).toHaveBeenNthCalledWith(2, "/tasks/?page=2");
  });

  it("returns an empty array when the first page has no results", async () => {
    mockedApiFetch.mockResolvedValueOnce(page([], null));

    const result = await fetchTasks();

    expect(result).toEqual([]);
  });
});

describe("fetchTask", () => {
  it("fetches a single task by id", async () => {
    const task = { id: 5 } as Task;
    mockedApiFetch.mockResolvedValueOnce(task);

    const result = await fetchTask(5);

    expect(mockedApiFetch).toHaveBeenCalledWith("/tasks/5/");
    expect(result).toBe(task);
  });
});

describe("createTask", () => {
  it("posts task data to the tasks endpoint", async () => {
    const created = { id: 1, name: "New task" } as Task;
    mockedApiFetch.mockResolvedValueOnce(created);

    const result = await createTask({ name: "New task" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/tasks/", {
      method: "POST",
      body: JSON.stringify({ name: "New task" }),
    });
    expect(result).toBe(created);
  });
});

describe("updateTask", () => {
  it("patches task data by id", async () => {
    const updated = { id: 3, name: "Updated" } as Task;
    mockedApiFetch.mockResolvedValueOnce(updated);

    const result = await updateTask(3, { name: "Updated" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/tasks/3/", {
      method: "PATCH",
      body: JSON.stringify({ name: "Updated" }),
    });
    expect(result).toBe(updated);
  });
});

describe("deleteTask", () => {
  it("deletes a task by id", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await deleteTask(7);

    expect(mockedApiFetch).toHaveBeenCalledWith("/tasks/7/", {
      method: "DELETE",
    });
  });
});
