import { afterEach, describe, expect, it, vi } from "vitest";

import { createSkill, deleteSkill, fetchGroups, fetchSkill, fetchSkills, updateSkill } from "./skills";
import { apiFetch } from "../utils/api";
import type { PlayerSkill } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchGroups", () => {
  it("fetches skill groups", async () => {
    const groups = [{ id: 1, name: "Fitness" }];
    mockedApiFetch.mockResolvedValueOnce(groups);

    const result = await fetchGroups();

    expect(mockedApiFetch).toHaveBeenCalledWith("/groups/");
    expect(result).toBe(groups);
  });
});

describe("fetchSkills", () => {
  it("unwraps the paginated results", async () => {
    const skills = [{ id: 1 }] as PlayerSkill[];
    mockedApiFetch.mockResolvedValueOnce({ results: skills });

    const result = await fetchSkills();

    expect(mockedApiFetch).toHaveBeenCalledWith("/skills/");
    expect(result).toBe(skills);
  });
});

describe("fetchSkill", () => {
  it("fetches a single skill by id", async () => {
    const skill = { id: 3 } as PlayerSkill;
    mockedApiFetch.mockResolvedValueOnce(skill);

    const result = await fetchSkill(3);

    expect(mockedApiFetch).toHaveBeenCalledWith("/skills/3/");
    expect(result).toBe(skill);
  });
});

describe("createSkill", () => {
  it("posts skill data", async () => {
    const created = { id: 1 } as PlayerSkill;
    mockedApiFetch.mockResolvedValueOnce(created);

    const result = await createSkill({ name: "New" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/skills/", {
      method: "POST",
      body: JSON.stringify({ name: "New" }),
    });
    expect(result).toBe(created);
  });
});

describe("updateSkill", () => {
  it("patches skill data by id", async () => {
    const updated = { id: 2 } as PlayerSkill;
    mockedApiFetch.mockResolvedValueOnce(updated);

    const result = await updateSkill(2, { name: "Updated" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/skills/2/", {
      method: "PATCH",
      body: JSON.stringify({ name: "Updated" }),
    });
    expect(result).toBe(updated);
  });
});

describe("deleteSkill", () => {
  it("deletes a skill by id", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await deleteSkill(4);

    expect(mockedApiFetch).toHaveBeenCalledWith("/skills/4/", {
      method: "DELETE",
    });
  });
});
