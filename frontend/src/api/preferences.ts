// src/api/preferences.ts
import type { UserPreferencesResponse } from "../types/api";
import { apiFetch } from "../utils/api";

export const fetchPreferences = async (): Promise<UserPreferencesResponse> => {
  return apiFetch<UserPreferencesResponse>("/me/preferences/");
};

export const updatePreferences = async (
  patch: Record<string, boolean>
): Promise<UserPreferencesResponse> => {
  return apiFetch<UserPreferencesResponse>("/me/preferences/", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
};
