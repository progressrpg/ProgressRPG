// src/api/tasks.ts
import type { Task, PaginatedResponse } from "../types";
import { apiFetch } from "../utils/api";

export async function fetchTasks(): Promise<Task[]> {
  const results: Task[] = [];
  let path: string | null = `/tasks/`;

  while (path) {
    const data: PaginatedResponse<Task> = await apiFetch<PaginatedResponse<Task>>(path);
    results.push(...data.results);
    path = data.next ? `/tasks/?${new URL(data.next).searchParams.toString()}` : null;
  }

  return results;
}

export function fetchTask(id: number): Promise<Task> {
  return apiFetch<Task>(`/tasks/${id}/`);
}

export function createTask(data: Partial<Task>): Promise<Task> {
  return apiFetch<Task>("/tasks/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export interface TaskUpdateResponse extends Task {
  completion_xp_gained: number;
  level_ups: number[];
}

export function updateTask(id: number, data: Partial<Task>): Promise<TaskUpdateResponse> {
  return apiFetch<TaskUpdateResponse>(`/tasks/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteTask(id: number): Promise<void> {
  return apiFetch<void>(`/tasks/${id}/`, {
    method: "DELETE",
  });
}
