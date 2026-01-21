import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { updatePlayer, downloadUserData, deleteAccount } from "../api/player";

export function useUpdatePlayer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updatePlayer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user"] });
    },
  });
}

export function useDownloadUserData() {
  return useMutation({
    mutationFn: downloadUserData,
  });
}

export function useDeleteAccount() {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      // Clear all cached data
      localStorage.clear();
      sessionStorage.clear();
      // Redirect to home page
      navigate("/");
    },
  });
}
