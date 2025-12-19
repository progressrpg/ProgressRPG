// src/api/activities.js
import { apiFetch } from "../../utils/api";
/*
Expected backend shape (example):
SkillGroup: { id, name, colour, icon }
Skill: { id, name, group, xp, level }
*/

export function fetchActivities() {
  return apiFetch(`/activities/`).then(data => data.results);
}

export function fetchActivity(id) {
  return apiFetch(`/activities/${id}/`);
}

export function createActivity(data) {
  return apiFetch("/activities/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateActivity(id, data) {
  return apiFetch(`/activities/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteActivity(id) {
  return apiFetch(`/activities/${id}/`, {
    method: "DELETE",
  });
}
