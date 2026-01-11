// src/api/tasks.js
import { apiFetch } from "../../utils/api";
/*
Expected backend shape (example):
Skill: { id, name, group, xp, level }
*/

export function fetchTasks() {
  return apiFetch(`/tasks/`).then(data => data.results);
}

export function fetchTask(id) {
  return apiFetch(`/tasks/${id}/`);
}

export function createTask(data) {
  return apiFetch("/tasks/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateTask(id, data) {
  return apiFetch(`/tasks/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteTask(id) {
  return apiFetch(`/tasks/${id}/`, {
    method: "DELETE",
  });
}
