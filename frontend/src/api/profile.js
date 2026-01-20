import { apiFetch } from "../../utils/api";

export const updateProfile = async (data) => {
  const response = await apiFetch("/me/profile/", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  return response;
};

export const downloadUserData = async () => {
  const accessToken = localStorage.getItem('accessToken');
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/download_user_data/`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to download user data');
  }

  const blob = await response.blob();

  // Create download link
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `user-data-${new Date().toISOString().split('T')[0]}.json`);
  document.body.appendChild(link);
  link.click();
  link.parentNode.removeChild(link);

  return { success: true };
};

export const deleteAccount = async () => {
  const response = await apiFetch("/delete_account/", {
    method: "DELETE",
  });
  return response;
};
