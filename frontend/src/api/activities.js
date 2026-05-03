// src/api/activities.js
import { apiFetch } from "../utils/api";
/*
Expected backend shape (example):
SkillGroup: { id, name, colour, icon }
Skill: { id, name, group, xp, level }
*/

export function fetchActivities() {
  return (async () => {
    const allResults = [];
    let page = 1;
    let hasNext = true;

    while (hasNext) {
      const data = await apiFetch(`/player-activities/?page=${page}`);
      const pageResults = Array.isArray(data?.results) ? data.results : [];
      allResults.push(...pageResults);
      hasNext = Boolean(data?.next);
      page += 1;
    }

    return allResults;
  })();
}

export function fetchActivity(id) {
  return apiFetch(`/player-activities/${id}/`);
}

export function createActivity(data) {
  return apiFetch("/player-activities/", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateActivity(id, data) {
  return apiFetch(`/player-activities/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteActivity(id) {
  return apiFetch(`/player-activities/${id}/`, {
    method: "DELETE",
  });
}
