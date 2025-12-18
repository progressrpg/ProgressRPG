// src/api/projects.js
import { apiFetch } from "../../utils/api";

export function fetchProjects() {
  return apiFetch("/projects/");
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
