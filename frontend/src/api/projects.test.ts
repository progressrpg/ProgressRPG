import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createProject,
  deleteProject,
  fetchProject,
  fetchProjects,
  updateProject,
} from "./projects";
import { apiFetch } from "../utils/api";
import type { Project } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchProjects", () => {
  it("unwraps the paginated results", async () => {
    const projects = [{ id: 1 }] as Project[];
    mockedApiFetch.mockResolvedValueOnce({ results: projects });

    const result = await fetchProjects();

    expect(mockedApiFetch).toHaveBeenCalledWith("/projects/");
    expect(result).toBe(projects);
  });
});

describe("fetchProject", () => {
  it("fetches a single project by id", async () => {
    const project = { id: 5 } as Project;
    mockedApiFetch.mockResolvedValueOnce(project);

    const result = await fetchProject(5);

    expect(mockedApiFetch).toHaveBeenCalledWith("/projects/5/");
    expect(result).toBe(project);
  });
});

describe("createProject", () => {
  it("posts project data", async () => {
    const created = { id: 1 } as Project;
    mockedApiFetch.mockResolvedValueOnce(created);

    const result = await createProject({ name: "New" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/projects/", {
      method: "POST",
      body: JSON.stringify({ name: "New" }),
    });
    expect(result).toBe(created);
  });
});

describe("updateProject", () => {
  it("patches project data by id", async () => {
    const updated = { id: 2 } as Project;
    mockedApiFetch.mockResolvedValueOnce(updated);

    const result = await updateProject(2, { name: "Updated" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/projects/2/", {
      method: "PATCH",
      body: JSON.stringify({ name: "Updated" }),
    });
    expect(result).toBe(updated);
  });
});

describe("deleteProject", () => {
  it("deletes a project by id", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await deleteProject(3);

    expect(mockedApiFetch).toHaveBeenCalledWith("/projects/3/", {
      method: "DELETE",
    });
  });
});
