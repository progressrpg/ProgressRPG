import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { updatePlayer, downloadUserData, deleteAccount, fetchDailyGoals } from "../api/player";
import { useAuth } from "../context/AuthContext";

// Query key shared with useActivityInput's refreshAfterActivityChange, which
// invalidates it after every completed task/session so the map view's daily
// goals badge (issue #673, redesigned in #751) updates immediately instead
// of waiting for the next poll.
export const DAILY_GOALS_QUERY_KEY = ["me", "daily-goals"];

// Polled lightly (rather than one-shot like other /me/ data) so the badge
// still rolls over to the new day's value on its own if the map view is left
// open across midnight, without needing a dedicated push mechanism for that.
const DAILY_GOALS_POLL_INTERVAL_MS = 60_000;

export function useDailyGoals() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: DAILY_GOALS_QUERY_KEY,
    queryFn: fetchDailyGoals,
    enabled: isAuthenticated,
    refetchInterval: DAILY_GOALS_POLL_INTERVAL_MS,
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
