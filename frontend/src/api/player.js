// src/api/player.js
import { apiFetch } from "../utils/api";

export const updatePlayer = async (data) => {
  const response = await apiFetch("/me/player/", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  return response;
};

export const downloadUserData = async () => {
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
  link.parentNode.removeChild(link);
  window.URL.revokeObjectURL(url);

  return { success: true };
};

export const deleteAccount = async () => {
  const response = await apiFetch("/delete_account/", {
    method: "DELETE",
  });
  return response;
};
