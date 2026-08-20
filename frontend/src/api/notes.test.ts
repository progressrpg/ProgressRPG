import { afterEach, describe, expect, it, vi } from "vitest";

import { createNote, deleteNote, fetchNote, fetchNoteFor, fetchNotes, updateNote } from "./notes";
import { apiFetch } from "../utils/api";
import type { Note } from "../types";

vi.mock("../utils/api", () => ({
  apiFetch: vi.fn(),
}));

const mockedApiFetch = apiFetch as ReturnType<typeof vi.fn>;

afterEach(() => {
  vi.clearAllMocks();
});

describe("fetchNotes", () => {
  it("unwraps the paginated results", async () => {
    const notes = [{ id: 1 }] as Note[];
    mockedApiFetch.mockResolvedValueOnce({ results: notes });

    const result = await fetchNotes();

    expect(mockedApiFetch).toHaveBeenCalledWith("/notes/");
    expect(result).toBe(notes);
  });
});

describe("fetchNote", () => {
  it("fetches a single note by id", async () => {
    const note = { id: 5 } as Note;
    mockedApiFetch.mockResolvedValueOnce(note);

    const result = await fetchNote(5);

    expect(mockedApiFetch).toHaveBeenCalledWith("/notes/5/");
    expect(result).toBe(note);
  });
});

describe("fetchNoteFor", () => {
  it("queries by task id when given a task link", async () => {
    const note = { id: 1 } as Note;
    mockedApiFetch.mockResolvedValueOnce({ results: [note] });

    const result = await fetchNoteFor({ task: 10 });

    expect(mockedApiFetch).toHaveBeenCalledWith("/notes/?task=10");
    expect(result).toBe(note);
  });

  it("queries by activity id when given an activity link", async () => {
    const note = { id: 2 } as Note;
    mockedApiFetch.mockResolvedValueOnce({ results: [note] });

    const result = await fetchNoteFor({ activity: 20 });

    expect(mockedApiFetch).toHaveBeenCalledWith("/notes/?activity=20");
    expect(result).toBe(note);
  });

  it("returns null when no note is linked", async () => {
    mockedApiFetch.mockResolvedValueOnce({ results: [] });

    const result = await fetchNoteFor({ task: 10 });

    expect(result).toBeNull();
  });
});

describe("createNote", () => {
  it("posts note data", async () => {
    const created = { id: 1 } as Note;
    mockedApiFetch.mockResolvedValueOnce(created);

    const result = await createNote({ body: "hi" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/notes/", {
      method: "POST",
      body: JSON.stringify({ body: "hi" }),
    });
    expect(result).toBe(created);
  });
});

describe("updateNote", () => {
  it("patches note data by id", async () => {
    const updated = { id: 2 } as Note;
    mockedApiFetch.mockResolvedValueOnce(updated);

    const result = await updateNote(2, { body: "updated" });

    expect(mockedApiFetch).toHaveBeenCalledWith("/notes/2/", {
      method: "PATCH",
      body: JSON.stringify({ body: "updated" }),
    });
    expect(result).toBe(updated);
  });
});

describe("deleteNote", () => {
  it("deletes a note by id", async () => {
    mockedApiFetch.mockResolvedValueOnce(undefined);

    await deleteNote(3);

    expect(mockedApiFetch).toHaveBeenCalledWith("/notes/3/", {
      method: "DELETE",
    });
  });
});
