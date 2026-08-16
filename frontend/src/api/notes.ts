// src/api/notes.ts
import type { Note, PaginatedResponse } from "../types";
import { apiFetch } from "../utils/api";

export function fetchNotes(): Promise<Note[]> {
  return apiFetch<PaginatedResponse<Note>>(`/notes/`).then((data) => data.results);
}

export function fetchNote(id: number): Promise<Note> {
  return apiFetch<Note>(`/notes/${id}/`);
}

/** The note linked to a given task or activity (catalog), if one exists. */
export async function fetchNoteFor(link: { task: number } | { activity: number }): Promise<Note | null> {
  const params = "task" in link ? `task=${link.task}` : `activity=${link.activity}`;
  const data = await apiFetch<PaginatedResponse<Note>>(`/notes/?${params}`);
  return data.results[0] ?? null;
}

export function createNote(data: Partial<Note>): Promise<Note> {
  return apiFetch<Note>("/notes/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateNote(id: number, data: Partial<Note>): Promise<Note> {
  return apiFetch<Note>(`/notes/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteNote(id: number): Promise<void> {
  return apiFetch<void>(`/notes/${id}/`, {
    method: "DELETE",
  });
}
