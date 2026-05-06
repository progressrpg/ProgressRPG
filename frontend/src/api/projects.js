// src/api/projects.js
import { apiFetch } from "../utils/api";

export function fetchProjects() {
  return apiFetch("/projects/").then((data) => data.results);
}

export function fetchProject(id) {
  return apiFetch(`/projects/${id}/`);
}

export function createProject(data) {
  return apiFetch("/projects/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateProject(id, data) {
  return apiFetch(`/projects/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteProject(id) {
  return apiFetch(`/projects/${id}/`, {
    method: "DELETE",
  });
}
