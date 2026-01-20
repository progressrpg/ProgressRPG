// src/api/categories.js
import { apiFetch } from "../../utils/api";
/*
Expected backend shape (example):
SkillGroup: { id, name, colour, icon }
Skill: { id, name, group, xp, level }
*/


export function fetchCategories() {
  return apiFetch(`/categories/`).then(data => data.results);
}

export function fetchCategory(id) {
  return apiFetch(`/categories/${id}/`);
}

export function createCategory(data) {
  return apiFetch("/categories/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateCategory(id, data) {
  return apiFetch(`/categories/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteCategory(id) {
  return apiFetch(`/categories/${id}/`, {
    method: "DELETE",
  });
}
