// src/api/player.ts
import type { Player } from "../types";
import { apiFetch } from "../utils/api";

export const updatePlayer = async (data: Partial<Player>): Promise<Player> => {
  const response = await apiFetch<Player>("/me/player/", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  return response;
};

export const downloadUserData = async (): Promise<{ success: true }> => {
  const response = await apiFetch("/download_user_data/", {
    method: 'GET',
    responseType: 'raw',
  });

  const blob = await response.blob();
  const contentDisposition = response.headers.get('Content-Disposition') || '';
  const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  const filename = filenameMatch?.[1] || `user-data-${new Date().toISOString().split('T')[0]}.json`;

  // Create download link
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.parentNode!.removeChild(link);
  window.URL.revokeObjectURL(url);

  return { success: true };
};

export const deleteAccount = async (): Promise<unknown> => {
  const response = await apiFetch("/delete_account/", {
    method: "DELETE",
  });
  return response;
};

export interface TodayPointsResponse {
  // null (not 0) when the player has no active PlayerCharacterLink - see
  // MeViewSet.today_points in api/views.py. Callers use this to hide the
  // map view's "today" badge entirely rather than showing a zero (issue #673).
  points_today: number | null;
}

export const fetchTodayPoints = async (): Promise<TodayPointsResponse> => {
  return apiFetch<TodayPointsResponse>("/me/today_points/");
};
