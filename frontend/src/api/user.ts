// src/api/user.ts
import type { TimezoneChoicesResponse } from "../types/api";
import type { User } from "../types/domain";
import { apiFetch } from "../utils/api";

export const fetchTimezoneChoices = async (): Promise<TimezoneChoicesResponse> => {
  return apiFetch<TimezoneChoicesResponse>("/me/timezone_choices/");
};

export const updateUserSettings = async (
  patch: Partial<Pick<User, "timezone">> & { day_start_time?: string }
): Promise<User> => {
  return apiFetch<User>("/me/user_settings/", {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
};
