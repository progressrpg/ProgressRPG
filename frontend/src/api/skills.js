// src/api/skills.js
import { apiFetch } from "../../utils/api";
/*
Expected backend shape (example):
SkillGroup: { id, name, colour, icon }
Skill: { id, name, group, xp, level }
*/

export function fetchGroups() {
  return apiFetch("/groups/");
}


export function fetchSkills() {
  return apiFetch(`/skills/`).then(data => data.results);
}

export function fetchSkill(id) {
  return apiFetch(`/skills/${id}/`);
}

export function createSkill(data) {
  return apiFetch("/skills/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateSkill(id, data) {
  return apiFetch(`/skills/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteSkill(id) {
  return apiFetch(`/skills/${id}/`, {
    method: "DELETE",
  });
}
