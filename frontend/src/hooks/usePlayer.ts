import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { updatePlayer, downloadUserData, deleteAccount, fetchTodayPoints } from "../api/player";
import { useAuth } from "../context/AuthContext";

// Query key shared with useActivityInput's refreshAfterActivityChange, which
// invalidates it after every completed task/session so the map view's
// "today" badge (issue #673) updates immediately instead of waiting for the
// next poll.
export const TODAY_POINTS_QUERY_KEY = ["me", "today-points"];

// Polled lightly (rather than one-shot like other /me/ data) so the badge
// still rolls over to the new day's value on its own if the map view is left
// open across midnight, without needing a dedicated push mechanism for that.
const TODAY_POINTS_POLL_INTERVAL_MS = 60_000;

export function useTodayPoints() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: TODAY_POINTS_QUERY_KEY,
    queryFn: fetchTodayPoints,
    enabled: isAuthenticated,
    refetchInterval: TODAY_POINTS_POLL_INTERVAL_MS,
  });
}

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
